import re
import uuid
import json
import time
import random
import asyncio
import discord
import datetime
import calendar

from io import BytesIO
from decimal import Decimal
from functools import partial
from collections import defaultdict

from discord import Interaction, Embed, Member, User, User, Member, SelectOption
from discord.ext.commands import Cog, command, Author, cooldown, BucketType, group, command, has_guild_permissions, bot_has_guild_permissions

from modules import config
from modules.styles import emojis, colors
from modules.evelinabot import Evelina
from modules.helpers import EvelinaContext
from modules.validators import ValidTime, ValidCompanyName, ValidCompanyTag, ValidCompanyDescription
from modules.converters import CashAmount, CardAmount, TransferAmount, BankAmount, DepositAmount, BetConverter, EligibleEconomyMember, NewRoleConverter, VaultDepositAmount, VaultWithdrawAmount, ProjectContributeAmount, ProjectCollectAmount, Amount
from modules.predicates import create_account, daily_taken, beg_taken, rob_taken, work_taken, slut_taken, bonus_taken, quest_taken, is_moderator, is_manager
from modules.persistent.economy import InviteView
from modules.economy.games import LadderButtons, BlackjackButtons, SlotsButtons, MinesButtons, RandomButtonView, CrashView, HigherLowerView, ConfirmView
from modules.economy.functions import EconomyMeasures, EconomyQuestsMeasures, CompanyInfoView, RequestView

class CardListView(discord.ui.View):
    def __init__(self, ctx, card_data):
        super().__init__()
        self.ctx = ctx
        self.card_data = card_data
        self.selected_business = None
        self.selected_sort_multiplier = None
        self.selected_sort_storage = None
        self.embeds = []
        self.current_page = 0

    async def get_filtered_data(self):
        filtered_data = self.card_data
        if self.selected_business:
            filtered_data = [
                c for c in filtered_data if 
                (await self.ctx.bot.db.fetchrow("SELECT business FROM economy_cards WHERE id = $1", c['id']))['business'] == self.selected_business
            ]
        if self.selected_sort_multiplier:
            multiplier_data = {
                c['id']: (await self.ctx.bot.db.fetchrow("SELECT multiplier FROM economy_cards_user WHERE id = $1", c['id']))['multiplier']
                for c in filtered_data
            }
            filtered_data.sort(
                key=lambda c: multiplier_data.get(c['id'], 0),
                reverse=(self.selected_sort_multiplier == "desc")
            )
        if self.selected_sort_storage:
            storage_data = {
                c['id']: (await self.ctx.bot.db.fetchrow("SELECT storage FROM economy_cards_user WHERE id = $1", c['id']))['storage']
                for c in filtered_data
            }
            filtered_data.sort(
                key=lambda c: storage_data.get(c['id'], 0),
                reverse=(self.selected_sort_storage == "desc")
            )
        return filtered_data

    async def populate_embeds(self):
        self.embeds.clear()
        filtered_data = await self.get_filtered_data()
        total_pages = len(filtered_data)
        for idx, card in enumerate(filtered_data):
            card_info = await self.ctx.bot.db.fetchrow("SELECT * FROM economy_cards WHERE id = $1", card['id'])
            if not card_info:
                continue
            item_name = card_info['name']
            item_stars = "⭐" * card_info['stars']
            item_file = card['image']
            embed = Embed(title=f"{item_name} | {item_stars}", color=colors.NEUTRAL)
            embed.set_author(name=self.ctx.author.name, icon_url=self.ctx.author.avatar.url if self.ctx.author.avatar else self.ctx.author.default_avatar.url)
            embed.set_image(url=item_file)
            embed.set_footer(text=f"Page: {idx + 1}/{total_pages} ({total_pages} entries)")
            self.embeds.append(embed)

    async def update_message(self, interaction: discord.Interaction):
        if not interaction.response.is_done():
            await interaction.response.defer()
        self.current_page = 0
        await self.populate_embeds()
        if not self.embeds:
            await interaction.edit_original_response(embed=Embed(description=f"{emojis.DENY} {self.ctx.author.mention}: No cards found", color=colors.ERROR), view=self)
        else:
            await interaction.edit_original_response(embed=self.embeds[self.current_page], view=self)

    async def update_page(self, interaction: discord.Interaction):
        if not interaction.response.is_done():
            await interaction.response.defer()
        if self.embeds:
            await interaction.edit_original_response(embed=self.embeds[self.current_page], view=self)

    @discord.ui.button(emoji=emojis.DOUBLELEFT, style=discord.ButtonStyle.primary)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 0
        await self.update_page(interaction)

    @discord.ui.button(emoji=emojis.LEFT, style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
        await self.update_page(interaction)

    @discord.ui.button(emoji=emojis.RIGHT, style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < len(self.embeds) - 1:
            self.current_page += 1
        await self.update_page(interaction)

    @discord.ui.button(emoji=emojis.DOUBLERIGHT, style=discord.ButtonStyle.primary)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = len(self.embeds) - 1
        await self.update_page(interaction)

    @discord.ui.select(
        placeholder="Select a Business Type...",
        options=[
            SelectOption(emoji="🏠", label="All", value="None", description="No filter for business type"),
            SelectOption(emoji="🏦", label="Business", value="business", description="Filter only Business cards"),
            SelectOption(emoji="🧪", label="Lab", value="lab", description="Filter only Lab cards"),
            SelectOption(emoji="💼", label="Personal", value="personal", description="Filter only Personal cards"),
        ]
    )
    async def business_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        await interaction.response.defer()
        self.selected_business = None if select.values[0] == "None" else select.values[0]
        await self.update_message(interaction)

    @discord.ui.select(
        placeholder="Sort by Multiplier...",
        options=[
            SelectOption(emoji=emojis.CANCEL, label="No Sorting", value="None", description="No filter for multiplier"),
            SelectOption(emoji=emojis.UP, label="Ascending", value="asc", description="Sorts by multiplier (ascending)"),
            SelectOption(emoji=emojis.DOWN, label="Descending", value="desc", description="Sorts by multiplier (descending)"),
        ]
    )
    async def multiplier_sort_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        await interaction.response.defer()
        self.selected_sort_multiplier = None if select.values[0] == "None" else select.values[0]
        await self.update_message(interaction)

    @discord.ui.select(
        placeholder="Sort by Storage...",
        options=[
            SelectOption(emoji=emojis.CANCEL, label="No Sorting", value="None", description="No filter for storage"),
            SelectOption(emoji=emojis.UP, label="Ascending", value="asc", description="Sorts by storage (ascending)"),
            SelectOption(emoji=emojis.DOWN, label="Descending", value="desc", description="Sorts by storage (descending)"),
        ]
    )
    async def storage_sort_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        await interaction.response.defer()
        self.selected_sort_storage = None if select.values[0] == "None" else select.values[0]
        await self.update_message(interaction)

class Economy(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        self._business = "🏦"
        self._lab = "🧪"
        self._company = "💼"
        self.cash = "💵"
        self._card = "💳"
        self.lock = asyncio.Lock()
        self.economy = EconomyMeasures(self.bot)
        self.quests = EconomyQuestsMeasures(self.bot)
        self.locks = defaultdict(asyncio.Lock)
        self.jobs = self.load_jobs()

    def load_jobs(self):
        with open("./data/jobs.txt") as f:
            return f.read().splitlines()
    
    def create_month_calendar(self, year, month, start_of_streak, today):
        _, days_in_month = calendar.monthrange(year, month)
        first_day_of_month = datetime.date(year, month, 1).weekday()
        weekdays = "Mo Tu We Th Fr Sa Su"
        marked_emoji = f"{emojis.ONLINE}"
        normal_emoji = f"{emojis.OFFLINE}"
        empty_emoji = "⬛"
        calendar_str = weekdays + "\n" + empty_emoji * first_day_of_month
        start_of_streak = start_of_streak.date()
        today = today.date()
        day_counter = first_day_of_month
        for day in range(1, days_in_month + 1):
            current_day = datetime.date(year, month, day)
            if start_of_streak <= current_day <= today:
                calendar_str += marked_emoji
            else:
                calendar_str += normal_emoji
            day_counter += 1
            if day_counter % 7 == 0:
                calendar_str += "\n"
                day_counter = 0
        if day_counter != 0:
            calendar_str += "\n"
        return calendar_str
    
    async def calculate_bonus(self, streak, user_id):
        is_donor = await self.bot.db.fetchval("SELECT EXISTS(SELECT 1 FROM donor WHERE user_id = $1)", user_id)
        bonus_percentage = 50 if streak >= 60 else 15 if streak >= 30 else 10 if streak >= 14 else 5 if streak >= 7 else 3 if streak >= 3 else 0
        donor_bonus_percentage = 20 if is_donor else 0
        total_bonus_percentage = bonus_percentage + donor_bonus_percentage
        return total_bonus_percentage
    
    @command(aliases=["with"], usage="withdraw 125", description="Withdraw card money to cash")
    @create_account()
    async def withdraw(self, ctx: EvelinaContext, amount: CardAmount):
        """Withdraw card money to cash"""
        async with self.locks[ctx.author.id]:
            check = await self.bot.db.fetchrow("SELECT cash, card FROM economy WHERE user_id = $1", ctx.author.id)
            card = check["card"]
            if card < amount:
                return await ctx.send_warning("You don't have enough money to withdraw")
            await self.bot.db.execute("UPDATE economy SET cash = $1, card = $2 WHERE user_id = $3", round(check["cash"] + amount, 2), round(card - amount, 2), ctx.author.id)
            await self.economy.logging(ctx.author, Decimal(amount), "withdraw", "bank")
            return await ctx.economy_send(f"Withdrew **{self.bot.misc.humanize_number(amount)}** {self._card}")

    @command(aliases=["dep"], usage="deposit 125", description="Deposit cash money to card")
    @create_account()
    async def deposit(self, ctx: EvelinaContext, amount: DepositAmount):
        """Deposit cash money to card"""
        async with self.locks[ctx.author.id]:
            check = await self.bot.db.fetchrow("SELECT cash, card, item_bank FROM economy WHERE user_id = $1", ctx.author.id)
            cash = check["cash"]
            current_card = check["card"]
            bank_limit = check["item_bank"]
            if cash < amount:
                return await ctx.send_warning("You don't have enough money to deposit")
            if current_card + amount > bank_limit:
                available_space = bank_limit - current_card
                amount = available_space
            await self.bot.db.execute("UPDATE economy SET cash = $1, card = $2 WHERE user_id = $3", round(cash - amount, 2), round(current_card + amount, 2), ctx.author.id)
            await self.economy.logging(ctx.author, Decimal(amount), "deposit", "bank")
            return await ctx.economy_send(f"Deposited **{self.bot.misc.humanize_number(amount)}** {self.cash}")

    @command(aliases=["give", "pay"], usage="transfer comminate 125", description="Transfer cash to a member")
    @create_account()
    async def transfer(self, ctx: EvelinaContext, member: EligibleEconomyMember, amount: TransferAmount):
        """Transfer cash to a member"""
        if member.id == ctx.author.id:
            return await ctx.send_warning("You can't transfer money to yourself.")

        async with self.locks[ctx.author.id], self.locks[member.id]:
            sender_data = await self.bot.db.fetchrow("SELECT cash, card FROM economy WHERE user_id = $1", ctx.author.id)
            receiver_data = await self.bot.db.fetchrow("SELECT cash, card, item_bank FROM economy WHERE user_id = $1", member.id)

            if isinstance(amount, str) and amount.lower() == 'all':
                max_transferable_amount = sender_data["card"]
                available_space = receiver_data["item_bank"] - receiver_data["card"]
                amount = min(max_transferable_amount, available_space)
            else:
                amount = float(amount)

            if amount <= 0:
                return await ctx.send_warning("You can't transfer **0** 💳")

            if sender_data["card"] < amount:
                return await ctx.send_warning("You don't have enough money on your **card** to transfer")

            if receiver_data["card"] + amount > receiver_data["item_bank"]:
                available_space = receiver_data["item_bank"] - receiver_data["card"]
                return await ctx.send_warning(f"{member.display_name} can only accept **{self.bot.misc.humanize_number(available_space)}** {self.cash} more due to the bank limit")

            yes_callback = partial(self.yes_callback, ctx.author.id, member.id, amount)
            no_callback = partial(self.no_callback, ctx.author.id)

            return await ctx.confirmation_send(
                f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to transfer **{self.bot.misc.humanize_number(amount)}** {self.cash} to {member.mention}?\n"
                f"> **Important:** When transferring money, a tax of 25% is charged.",
                yes_callback,
                no_callback
            )
    async def yes_callback(self, sender_id, receiver_id, amount, interaction: Interaction):
            async with self.locks[sender_id], self.locks[receiver_id]:
                sender_data = await self.bot.db.fetchrow("SELECT cash, card FROM economy WHERE user_id = $1", sender_id)
                receiver_data = await self.bot.db.fetchrow("SELECT cash, card, item_bank FROM economy WHERE user_id = $1", receiver_id)

                if amount <= 0:
                    return await interaction.response.edit_message(
                        embed=Embed(description=f"{emojis.WARNING} You can't transfer **0** 💳", color=colors.WARNING), view=None
                    )

                if sender_data["card"] < amount:
                    return await interaction.response.edit_message(
                        embed=Embed(description=f"{emojis.WARNING} You don't have enough money on your **card** to transfer", color=colors.WARNING), view=None
                    )

                if receiver_data["card"] + amount > receiver_data["item_bank"]:
                    available_space = receiver_data["item_bank"] - receiver_data["card"]
                    return await interaction.response.edit_message(
                        embed=Embed(description=f"{emojis.WARNING} {interaction.user.mention} can only accept **{self.bot.misc.humanize_number(available_space)}** {self.cash} more due to the bank limit.", color=colors.WARNING), view=None
                    )

                await self.bot.db.execute(
                    "UPDATE economy SET card = $1 WHERE user_id = $2",
                    round(sender_data["card"] - amount, 2), sender_id
                )
                await self.bot.db.execute(
                    "UPDATE economy SET card = $1 WHERE user_id = $2",
                    round(receiver_data["card"] + (amount * 0.75), 2), receiver_id
                )

                await self.economy.logging(interaction.user, Decimal(amount), "transfered", f"<@{receiver_id}>")
                await self.economy.logging(self.bot.get_user(receiver_id), Decimal(amount * 0.75), "received", f"<@{sender_id}>")

                await interaction.response.edit_message(
                    embed=Embed(description=f"{emojis.APPROVE} {interaction.user.mention}: Successfully transferred **{self.bot.misc.humanize_number(amount)}** {self.cash} (`{self.bot.misc.humanize_number(amount * 0.75)}`) to <@{receiver_id}>", color=colors.SUCCESS),
                    view=None
                )
    async def no_callback(interaction: Interaction):
            await interaction.response.edit_message(embed=Embed(description=f"{emojis.DENY} {interaction.user.mention}: Transfer got canceled", color=colors.ERROR), view=None)

    @command(aliases=["bal"], usage="balance comminate", description="Check someone's balance and rank")
    @create_account()
    async def balance(self, ctx: EvelinaContext, *, member: User = Author):
        """Check someone's balance and rank"""
        check = await self.bot.db.fetchrow("SELECT cash, card, item_bank FROM economy WHERE user_id = $1", member.id)
        if not check:
            return await ctx.send_warning(f"Member doesn't have any **money**")
        user_total = check["cash"] + check["card"]
        all_users = await self.bot.db.fetch("SELECT user_id, cash, card FROM economy")
        total_sums = []
        for user in all_users:
            if user['user_id'] in self.bot.owner_ids:
                continue
            if not self.bot.get_user(user["user_id"]):
                continue
            total_sum = user["cash"] + user["card"]
            total_sums.append(total_sum)
        total_sums.append(user_total)
        total_sums.sort(reverse=True)
        rank = total_sums.index(user_total) + 1
        business = await self.economy.get_user_business(member.id)
        laboratory = await self.bot.db.fetchrow("SELECT * FROM economy_lab WHERE user_id = $1", member.id)
        if laboratory:
            time_passed = datetime.datetime.now().timestamp() - laboratory['last_collected']
            if time_passed < 3600:
                earnings = 0
            hours_passed = time_passed // 3600
            earnings_per_hour, earnings_cap, _ = await self.economy.calculate_lab_earnings_and_upgrade(member.id, laboratory['upgrade_state'])
            earnings = earnings_per_hour * hours_passed
            if earnings > earnings_cap:
                earnings = earnings_cap
        embed = Embed(color=colors.NEUTRAL)
        embed.set_author(name=f"{member.name}'s balance", icon_url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.add_field(name=f"{self.cash} Cash", value=self.bot.misc.humanize_number(check["cash"]), inline=True)
        embed.add_field(name=f"{self._card} Card", value=f"{self.bot.misc.humanize_number(check['card'])} / {self.bot.misc.humanize_number(check['item_bank'])}", inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        if business:
            system_business = await self.economy.get_system_business_by_id(business['business_id']) if business else None
            embed.add_field(name=f"{self._business} Business", value=f"{self.bot.misc.humanize_number(await self.economy.calculate_business_earning(member.id, business['last_collected'], system_business['earnings']))}")
        else:
            embed.add_field(name=f"{self._business} Business", value="N/A")
        if laboratory:
            embed.add_field(name=f"{self._lab} Laboratory", value=f"{self.bot.misc.humanize_number(earnings)}")
        else:
            embed.add_field(name=f"{self._lab} Laboratory", value="N/A")
        company = await self.economy.get_user_company(member.id)
        if company:
            company_earnings = await self.bot.db.fetchrow("SELECT amount FROM company_earnings WHERE user_id = $1 AND company_id = $2", member.id, company['id'])
            embed.add_field(name=f"{self._company} Company", value=f"{self.bot.misc.humanize_number(company_earnings['amount']) if company_earnings else self.bot.misc.humanize_number(0)}")
        else:
            embed.add_field(name=f"{self._company} Company", value="N/A")
        embed.set_footer(text=f"Rank #{rank} out of {len(total_sums)}")
        return await ctx.send(embed=embed)

    @command(aliases=["lb"], description="Global leaderboard for the economy")
    @create_account()
    async def leaderboard(self, ctx: EvelinaContext):
        """Global leaderboard for the economy"""
        results = await self.bot.db.fetch("SELECT user_id, cash, card FROM economy ORDER BY cash + card DESC LIMIT 100")
        if not results:
            return await ctx.send_warning("No one has any cash yet.")
        to_show = []
        for check in results:
            if check['user_id'] not in self.bot.owner_ids:
                user = self.bot.get_user(check['user_id']) or f"<@{check['user_id']}>"
                company = await self.economy.get_user_company(check['user_id'])
                company_tag = f" | {company['tag']}" if company else ''
                to_show.append(
                    f"**{user}{company_tag}** (`{check['user_id']}`)\n> {self.bot.misc.humanize_number(round(check['cash'], 2))} {self.cash} | {self.bot.misc.humanize_number(round(check['card'], 2))} {self._card}"
                )
        if not to_show:
            return await ctx.send_warning("No one has any cash yet.")
        return await ctx.smallpaginate(to_show[:100], f"Global economy leaderboard", {"name": ctx.author, "icon_url": ctx.author.avatar})

    @command(aliases=["glb"], description="Guild leaderboard for the economy")
    @create_account()
    async def guildleaderboard(self, ctx: EvelinaContext):
        """Guild leaderboard for the economy"""
        server_member_ids = tuple(member.id for member in ctx.guild.members)
        if not server_member_ids:
            return await ctx.send_warning("No one in this server has any cash yet.")
        query = f"SELECT user_id, cash, card FROM economy WHERE user_id = ANY($1::bigint[])"
        results = await self.bot.db.fetch(query, list(server_member_ids))
        if not results:
            return await ctx.send_warning("No one has any cash yet.")
        sorted_results = sorted(
            results,
            key=lambda c: c["cash"] + c["card"], 
            reverse=True
        )
        to_show = [
            f"**{self.bot.get_user(check['user_id'])}{' | ' + (await self.economy.get_user_company(check['user_id']))['tag'] if await self.economy.get_user_company(check['user_id']) else ''}** (`{check['user_id']}`)\n> {self.bot.misc.humanize_number(round(check['cash'], 2))} {self.cash} | {self.bot.misc.humanize_number(round(check['card'], 2))} {self._card}"
            for check in sorted_results if self.bot.get_user(check['user_id']) and check['user_id'] not in self.bot.owner_ids
        ]
        if not to_show:
            return await ctx.send_warning("No one has any cash yet.")
        return await ctx.smallpaginate(to_show[:500], f"Guild economy leaderboard", {"name": ctx.author, "icon_url": ctx.author.avatar})

    @command(aliases=["clb"], description="Cash leaderboard for the economy")
    @create_account()
    async def cashleaderboard(self, ctx: EvelinaContext):
        """Cash leaderboard for the economy"""
        results = await self.bot.db.fetch("SELECT user_id, cash, card FROM economy ORDER BY cash DESC LIMIT 1000")
        if not results:
            return await ctx.send_warning("No one has any cash yet.")
        server_members = {member.id for member in ctx.guild.members}
        sorted_results = [
            result for result in results
            if result['user_id'] in server_members and result['user_id'] not in self.bot.owner_ids
        ]
        to_show = [
            f"**{self.bot.get_user(result['user_id'])}{' | ' + (await self.economy.get_user_company(result['user_id']))['tag'] if await self.economy.get_user_company(result['user_id']) else ''}** (`{result['user_id']}`)\n> {self.bot.misc.humanize_number(round(result['cash'], 2))} {self.cash} | {self.bot.misc.humanize_number(round(result['card'], 2))} {self._card}"
            for result in sorted_results if self.bot.get_user(result['user_id'])
        ]
        if not to_show:
            return await ctx.send_warning("No one has any cash yet.")
        return await ctx.smallpaginate(to_show[:500], f"Cash economy leaderboard", {"name": ctx.author, "icon_url": ctx.author.avatar})

    @command(aliases=["nlb"], description="Networth leaderboard for the economy")
    @create_account()
    async def networthleaderboard(self, ctx: EvelinaContext):
        """Networth leaderboard for the economy"""
        results = await self.bot.db.fetch("SELECT user_id FROM economy")
        if not results:
            return await ctx.send_warning("No one has any networth yet.")
        server_members = {member.id for member in ctx.guild.members}
        sorted_results = [
            result for result in results
            if result['user_id'] in server_members and result['user_id'] not in self.bot.owner_ids
        ]
        user_ids = [result['user_id'] for result in sorted_results]
        networths = await asyncio.gather(*(self.economy.get_user_networth(user_id) for user_id in user_ids))
        leaderboard = []
        for user_id, networth in zip(user_ids, networths):
            user = self.bot.get_user(user_id)
            if user:
                company = await self.economy.get_user_company(user_id)
                company_tag = f" | {company['tag']}" if company else ""
                leaderboard.append(
                    f"**{user}{company_tag}** (`{user_id}`)\n> Networth: {self.bot.misc.humanize_number(round(networth, 2))} {self.cash}"
                )
        if not leaderboard:
            return await ctx.send_warning("No one has any networth yet.")
        leaderboard.sort(key=lambda x: float(x.split("Networth: ")[1].split()[0].replace(",", "")), reverse=True)
        return await ctx.smallpaginate(leaderboard[:500], f"Networth economy leaderboard", {"name": ctx.author, "icon_url": ctx.author.avatar})

    @command(aliases=["gamble"], usage="dice 125", cooldown=5, description="Play a dice game")
    @create_account()
    @cooldown(1, 5, BucketType.user)
    async def dice(self, ctx: EvelinaContext, amount: CashAmount):
        """Play a dice game"""
        async with self.locks[ctx.author.id]:
            check = await self.bot.db.fetchrow("SELECT * FROM economy WHERE user_id = $1", ctx.author.id)
            cash = check["cash"]
            if amount < 10:
                return await ctx.send_warning(f"You can't bet less than **10** {self.cash}")
            await self.economy.logging(ctx.author, Decimal(amount), "gamble", "dice")
            user_dice = random.randint(1, 6) + random.randint(1, 6)
            bot_dice = random.randint(1, 6) + random.randint(1, 6)
            if ctx.author.id in self.bot.owner_ids:
                bot_dice = random.randint(1, 4) + random.randint(1, 4)
            if user_dice > bot_dice:
                e = Embed(color=colors.SUCCESS, description=f"{emojis.WIN} {ctx.author.mention}: You have rolled **{user_dice}** and the bot has rolled **{bot_dice}**.\n> You won **{self.bot.misc.humanize_number(amount)}** {self.cash}, in total you have **{self.bot.misc.humanize_number(round(cash + amount, 2))}** {self.cash}")
                await self.quests.add_win_game(ctx.author, "dice")
                await self.quests.add_win_money(ctx.author, "dice", Decimal(amount))
                await self.bot.db.execute("UPDATE economy SET cash = $1 WHERE user_id = $2", round(cash + amount, 2), ctx.author.id)
                await self.economy.logging(ctx.author, Decimal(amount), "won", "dice")
            elif bot_dice > user_dice:
                e = Embed(color=colors.ERROR, description=f"{emojis.LOSE} {ctx.author.mention}: You have rolled **{user_dice}** and the bot has rolled **{bot_dice}**.\n> You lost **{self.bot.misc.humanize_number(amount)}** {self.cash}, in total you have **{self.bot.misc.humanize_number(round(cash - amount, 2))}** {self.cash}")
                await self.bot.db.execute("UPDATE economy SET cash = $1 WHERE user_id = $2", round(cash - amount, 2), ctx.author.id)
                await self.economy.logging(ctx.author, Decimal(amount), "lost", "dice")
            else:
                e = Embed(color=colors.ECONOMY, description=f"{emojis.TIE} {ctx.author.mention}: You have rolled **{user_dice}** and the bot has rolled **{bot_dice}**.\n> It's a tie, in total you have **{self.bot.misc.humanize_number(cash)}** {self.cash}")
                await self.economy.logging(ctx.author, Decimal(amount), "tie", "dice")
            await ctx.reply(embed=e)

    @command(aliases=["ro"], usage="roulette 125 red", cooldown=5, description="Play a roulette game")
    @create_account()
    @cooldown(1, 5, BucketType.user)
    async def roulette(self, ctx: EvelinaContext, amount: CashAmount, bet: BetConverter):
        """Play a roulette game"""
        async with self.locks.setdefault(ctx.author.id, asyncio.Lock()):
            check = await self.bot.db.fetchrow("SELECT * FROM economy WHERE user_id = $1", ctx.author.id)
            cash = check["cash"]
            if amount < 10:
                return await ctx.send(f"You can't bet less than **10** {self.cash}")
            await self.economy.logging(ctx.author, Decimal(amount), "gamble", "roulette")
            embed = Embed(color=colors.ECONOMY, description=f"🎲 {ctx.author.mention}: Spinning the roulette...")
            mes = await ctx.reply(embed=embed)
            data = await self.bot.session.get_json(
                f"https://api.evelina.bot/roulette?bet={bet}&amount={amount}&key=X3pZmLq82VnHYTd6Cr9eAw"
            )
            roll_number = data["roll"]["number"]
            roll_color = data["roll"]["color"]
            roll_parity = data["roll"]["parity"]
            roll_dozen = data["roll"].get("dozen", "unknown")
            win = data["bet"]["win"]
            payout = float(data["bet"]["payout"])
            if not win:
                new_cash = cash - amount
                message = (f"{emojis.LOSE} {ctx.author.mention}: The ball landed on **{roll_number}** __{roll_color}__ (`{roll_parity}`, `{roll_dozen}`)\n"
                           f"> You lost **{self.bot.misc.humanize_number(amount)}** {self.cash}, in total you have **{self.bot.misc.humanize_number(new_cash)}** {self.cash}")
                color = colors.ERROR
                await self.economy.logging(ctx.author, Decimal(amount), "lost", "roulette")
            else:
                real_cash = cash - amount
                new_cash = real_cash + payout
                message = (f"{emojis.WIN} {ctx.author.mention}: The ball landed on **{roll_number}** __{roll_color}__ (`{roll_parity}`, `{roll_dozen}`)\n"
                           f"> You won **{self.bot.misc.humanize_number(payout)}** {self.cash}, in total you have **{self.bot.misc.humanize_number(new_cash)}** {self.cash}")
                color = colors.SUCCESS
                await self.quests.add_win_game(ctx.author, "roulette")
                await self.quests.add_win_money(ctx.author, "roulette", Decimal(payout))
                await self.economy.logging(ctx.author, Decimal(payout), "won", "roulette")
            await self.bot.db.execute("UPDATE economy SET cash = $1 WHERE user_id = $2", new_cash, ctx.author.id)
            embed = Embed(color=color, description=message)
            await mes.edit(embed=embed)

    @command(aliases=["cf"], usage="coinflip 125 heads", cooldown=5, description="Play a coinflip game")
    @create_account()
    @cooldown(1, 5, BucketType.user)
    async def coinflip(self, ctx: EvelinaContext, amount: CashAmount, bet: str):
        """Play a coinflip game"""
        async with self.locks[ctx.author.id]:
            check = await self.bot.db.fetchrow("SELECT * FROM economy WHERE user_id = $1", ctx.author.id)
            cash = check["cash"]
            if amount < 10:
                return await ctx.send_warning(f"You can't bet less than **10** {self.cash}")
            if not bet.lower() in ["heads", "tails"]:
                return await ctx.send_warning("You can only bet on **heads** or **tails**")
            await self.economy.logging(ctx.author, Decimal(amount), "gamble", "coinflip")
            response = random.choice(["heads", "tails"])
            if response == bet.lower():
                e = Embed(color=colors.SUCCESS, description=f"{emojis.WIN} {ctx.author.mention}: It's **{response}**\n> You won **{self.bot.misc.humanize_number(amount)}** {self.cash}, in total you have **{self.bot.misc.humanize_number(round(cash + amount, 2))}** {self.cash}")
                await self.quests.add_win_game(ctx.author, "coinflip")
                await self.quests.add_win_money(ctx.author, "coinflip", Decimal(amount))
                await self.bot.db.execute("UPDATE economy SET cash = $1 WHERE user_id = $2", round(cash + amount, 2), ctx.author.id)
                await self.economy.logging(ctx.author, Decimal(amount), "won", "coinflip")
            else:
                e = Embed(color=colors.ERROR, description=f"{emojis.LOSE} {ctx.author.mention}: You chose **{bet.lower()}**, but it's **{response}**\n> You lost **{self.bot.misc.humanize_number(amount)}** {self.cash}, in total you have **{self.bot.misc.humanize_number(round(cash - amount, 2))}** {self.cash}")
                await self.bot.db.execute("UPDATE economy SET cash = $1 WHERE user_id = $2", round(cash - amount, 2), ctx.author.id)
                await self.economy.logging(ctx.author, Decimal(amount), "lost", "coinflip")
            await ctx.reply(embed=e)

    @command(aliases=["bj"], usage="blackjack 125", cooldown=5, description="Start a blackjack game")
    @create_account()
    @cooldown(1, 5, BucketType.user)
    async def blackjack(self, ctx: EvelinaContext, amount: CashAmount):
        """Start a blackjack game"""
        if amount < 10:
            return await ctx.send_warning(f"You can't bet less than **10** {self.cash}")
        await self.economy.logging(ctx.author, Decimal(amount), "gamble", "blackjack")
        embed = Embed(title=f"Playing Blackjack with {amount:,.2f} {self.cash}", color=colors.NEUTRAL)
        embed.add_field(name=f"{ctx.author}", value="Hit 'Hit' to start the game.", inline=True)
        embed.add_field(name="Dealer", value="Hit 'Hit' to start the game.", inline=True)
        view = BlackjackButtons(ctx, amount, self.bot)
        message = await ctx.reply(embed=embed, view=view)
        view.message = message

    @command(name="slot", aliases=["slots"], usage="slot 125")
    async def slot(self, ctx: EvelinaContext, amount: CashAmount):
        """Play a slot machine game"""
        if await self.bot.cache.get(f"slot_user_{ctx.author.id}"):
            return await ctx.send_warning("You **already** have an active slot game.")
        if await self.bot.cache.get(f"slot_channel_{ctx.channel.id}"):
            return await ctx.send_warning("There is **already an active slot game** in this channel.")
        await self.economy.logging(ctx.author, Decimal(amount), "gamble", "slot")
        embed = Embed(color=colors.ECONOMY, description=f"### 🎰 Slot Machine",)
        embed.add_field(name="\u200b", value="Press Hit to start.", inline=False)
        embed.add_field(name="Bet", value=f"{amount:,.2f} {self.cash}", inline=False)
        view = SlotsButtons(ctx, amount, self.bot)
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    @command(name="ladder", usage="ladder 125", cooldown=5, description="Start a ladder game")
    @create_account()
    @cooldown(1, 5, BucketType.user)
    async def ladder(self, ctx: EvelinaContext, amount: CashAmount):
        """Start a ladder game"""
        if amount < 10:
            return await ctx.send_warning(f"You can't bet less than **10** {self.cash}")
        await self.economy.logging(ctx.author, Decimal(amount), "gamble", "ladder")
        await self.bot.db.execute("UPDATE economy SET cash = cash - $1 WHERE user_id = $2", amount, ctx.author.id)
        view = LadderButtons(ctx, amount, self.bot)
        embed = view.create_embed()
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    @command(name="mines", usage="mines 125 4", cooldown=5, description="Start a mines game")
    @create_account()
    @cooldown(1, 5, BucketType.user)
    async def mines(self, ctx: EvelinaContext, amount: CashAmount, count: int = 4):
        """Start a mines game"""
        if amount < 10:
            return await ctx.send_warning(f"You can't bet less than **10** {self.cash}")
        protected_ids = [206832952980668428, 335500798752456705] #[comminate, welovecatcher]
        grid_size = 4
        if count < 1 or count > 15:
            return await ctx.send_warning("The number of mines must be between 1 and 15.")
        mines = MinesButtons.generate_mines_static(grid_size, count)
        if ctx.author.id in protected_ids:
            mines_display = [["⬜" for _ in range(grid_size)] for _ in range(grid_size)]
            for x, y in mines:
                mines_display[x][y] = "💣"
            mines_str = "\n".join(" ".join(row) for row in mines_display)
            await ctx.author.send(f"**{ctx.author.name}**, here is the mines grid:\n{mines_str}")
        await self.economy.logging(ctx.author, Decimal(amount), "gamble", "mines")
        await self.bot.db.execute("UPDATE economy SET cash = cash - $1 WHERE user_id = $2", amount, ctx.author.id)
        multipliers = [1.02, 1.06, 1.12, 1.19, 1.28, 1.39, 1.53, 1.74, 2.05, 2.27, 2.56, 2.98, 3.59, 4.63, 6.69]
        view = MinesButtons(ctx, amount, self.bot, mines, count, multipliers)
        embed = view.create_embed()
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    @command(name="crash", usage="crash 125", cooldown=5, description="Start a crash game")
    @create_account()
    @cooldown(1, 5, BucketType.user)
    async def crash(self, ctx: EvelinaContext, amount: CashAmount):
        """Start a crash game"""
        if amount < 10:
            return await ctx.send_warning(f"You can't bet less than **10** {self.cash}")
        await self.economy.logging(ctx.author, Decimal(amount), "gamble", "crash")
        await self.bot.db.execute("UPDATE economy SET cash = cash - $1 WHERE user_id = $2", amount, ctx.author.id)
        embed = Embed(
            title=f"Playing Crash with {amount:,.2f} {self.cash}",
            description="> Starting the game...",
            color=colors.NEUTRAL
        )
        embed.add_field(name="Multiplier", value=f"1.00x", inline=True)
        embed.add_field(name="Winnings", value=f"{amount:,.2f} {self.cash}", inline=True)
        view = CrashView(ctx, amount, self.bot)
        message = await ctx.reply(embed=embed, view=view)
        view.message = message
        await view.start_crash()

    @command(name="higherlower", aliases=["hl"], usage="higherlower 125", cooldown=5, description="Guess if the number is higher or lower")
    @create_account()
    @cooldown(1, 5, BucketType.user)
    async def higherlower(self, ctx: EvelinaContext, amount: CashAmount):
        """Guess if the number is higher or lower"""
        if amount < 10:
            return await ctx.send_warning(f"You can't bet less than **10** {self.cash}")
        await self.economy.logging(ctx.author, Decimal(amount), "gamble", "higherlower")
        await self.bot.db.execute("UPDATE economy SET cash = cash - $1 WHERE user_id = $2", amount, ctx.author.id)
        view = HigherLowerView(ctx, amount, self.bot)
        embed = view.create_embed()
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    @command(name="beg", description="Beg for money")
    @create_account()
    @beg_taken()
    @cooldown(1, 5, BucketType.user)
    async def beg(self, ctx: EvelinaContext):
        """Beg for money"""
        check = await self.bot.db.fetchrow("SELECT * FROM economy WHERE user_id = $1", ctx.author.id)
        if check["cash"] + check["card"] > 100000:
            return await ctx.send_warning(f"You can't beg if you have more than **100.000** {self.cash}")
        min_win = await self.bot.db.fetchval("SELECT beg_min FROM economy_config WHERE active = True")
        max_win = await self.bot.db.fetchval("SELECT beg_max FROM economy_config WHERE active = True")
        received = random.uniform(min_win, max_win)
        await self.quests.add_collect_money(ctx.author, "beg", Decimal(received))
        await self.bot.db.execute("UPDATE economy SET beg = $1, cash = cash + $2 WHERE user_id = $3", int((datetime.datetime.now() + datetime.timedelta(minutes=1)).timestamp()), received, ctx.author.id)
        description = f"🙏 {ctx.author.mention}: You begged and received **{self.bot.misc.humanize_number(received)}** {self.cash}"
        await self.economy.logging(ctx.author, Decimal(received), "collect", "beg")
        embed = Embed(color=colors.ECONOMY, description=description)
        return await ctx.send(embed=embed)

    @command(name="bonus", description="Claim your bonus cash")
    @create_account()
    @bonus_taken()
    @cooldown(1, 5, BucketType.user)
    async def bonus(self, ctx: EvelinaContext):
        """Claim your bonus cash"""
        min_win = await self.bot.db.fetchval("SELECT bonus_min FROM economy_config WHERE active = True")
        max_win = await self.bot.db.fetchval("SELECT bonus_max FROM economy_config WHERE active = True")
        amounts = [random.randint(min_win, max_win) for _ in range(3)]
        random.shuffle(amounts)
        await self.bot.db.execute("UPDATE economy SET bonus = $1 WHERE user_id = $2", int((datetime.datetime.now() + datetime.timedelta(minutes=15)).timestamp()), ctx.author.id)
        view = RandomButtonView(ctx, amounts, self.bot)
        await ctx.evelina_send("Click a button to reveal your prize!", view=view)

    @command(name="work", description="Work a job and earn money")
    @create_account()
    @work_taken()
    @cooldown(1, 5, BucketType.user)
    async def work(self, ctx: EvelinaContext):
        """Work a job and earn money"""
        jobname = random.choice(self.jobs)
        check = await self.bot.db.fetchrow("SELECT * FROM economy WHERE user_id = $1", ctx.author.id)
        cash = check["cash"]
        company = await self.economy.get_user_company(ctx.author.id)
        if company:
            limit = await self.economy.get_level_info(company['level'])
            received = limit['earnings']
            description = f"{self._company} {ctx.author.mention}: You worked for **{company['name']}** and received **{self.bot.misc.humanize_number(received)}** {self.cash}"
            new_cash = round(cash + received, 2)
            await self.quests.add_collect_money(ctx.author, "work", Decimal(received))
            await self.bot.db.execute("UPDATE economy SET work = $1, cash = $2 WHERE user_id = $3", int((datetime.datetime.now() + datetime.timedelta(hours=1)).timestamp()), new_cash, ctx.author.id)
        else:
            jobname_formatted = jobname.upper().replace(" ", "_")
            emoji = getattr(emojis, jobname_formatted, "")
            min_win = await self.bot.db.fetchval("SELECT work_min FROM economy_config WHERE active = True")
            max_win = await self.bot.db.fetchval("SELECT work_max FROM economy_config WHERE active = True")
            received = round(random.uniform(min_win, max_win), 2)
            description = f"{emoji} {ctx.author.mention}: You were working as a **{jobname}** and received **{self.bot.misc.humanize_number(received)}** {self.cash}"
            new_cash = round(cash + received, 2)
            await self.quests.add_collect_money(ctx.author, "work", Decimal(received))
            await self.bot.db.execute("UPDATE economy SET work = $1, cash = $2 WHERE user_id = $3", int((datetime.datetime.now() + datetime.timedelta(hours=1)).timestamp()), new_cash, ctx.author.id)
        await self.economy.logging(ctx.author, Decimal(received), "collect", "work")
        embed = Embed(color=colors.ECONOMY, description=description)
        return await ctx.send(embed=embed)

    @command(name="slut", description="Work as a prostitute for money")
    @create_account()
    @slut_taken()
    @cooldown(1, 5, BucketType.user)
    async def slut(self, ctx: EvelinaContext):
        """Work as a prostitute for money"""
        min_win = await self.bot.db.fetchval("SELECT slut_min FROM economy_config WHERE active = True")
        max_win = await self.bot.db.fetchval("SELECT slut_max FROM economy_config WHERE active = True")
        received = random.uniform(min_win, max_win)
        await self.quests.add_collect_money(ctx.author, "slut", Decimal(received))
        await self.bot.db.execute("UPDATE economy SET slut = $1, cash = cash + $2 WHERE user_id = $3", int((datetime.datetime.now() + datetime.timedelta(hours=1)).timestamp()), received, ctx.author.id)
        description = f"💋 {ctx.author.mention}: You worked as a **prostitute** and earned **{self.bot.misc.humanize_number(received)}** {self.cash}"
        await self.economy.logging(ctx.author, Decimal(received), "collect", "slut")
        embed = Embed(color=colors.ECONOMY, description=description)
        return await ctx.send(embed=embed)

    @command(name="rob", usage="rob comminate", description="Attempt to steal money from another player")
    @create_account()
    @rob_taken()
    @cooldown(1, 5, BucketType.user)
    async def rob(self, ctx: EvelinaContext, member: Member):
        """Attempt to steal money from another player"""
        if member.id in self.bot.owner_ids:
            return await ctx.send_warning("You can't steal money from a bot owner")
        if member.id == ctx.author.id:
            return await ctx.send_warning("You can't steal from yourself!")
        check = await self.bot.db.fetchrow("SELECT cash, card FROM economy WHERE user_id = $1", ctx.author.id)
        target_balance = await self.bot.db.fetchval("SELECT cash FROM economy WHERE user_id = $1", member.id)
        if not target_balance or target_balance < 10:
            return await ctx.send_warning(f"**{member.name}** has no money to steal.")
        if check["card"] < 50000:
            return await ctx.send_warning(f"You need at least **50,000** {self.cash} on your card to rob someone.")
        rob_chance = 1.00
        card_used = await self.bot.db.fetchrow("SELECT * FROM economy_cards_used WHERE user_id = $1 AND business = $2", member.id, "personal")
        if card_used:
            card_user = await self.bot.db.fetchrow("SELECT * FROM economy_cards_user WHERE user_id = $1 AND card_id = $2", member.id, card_used["card_id"])
            if card_user:
                card_info = await self.bot.db.fetchrow("SELECT * FROM economy_cards WHERE id = $1", card_user["id"])
                if card_info:
                    rob_chance = (100 - card_user["storage"]) / 100
        if random.random() < rob_chance:
            stolen_amount = round(target_balance * 0.1, 2)
            if stolen_amount > 1000000:
                real_stolen_amount = 1000000
            else:
                real_stolen_amount = stolen_amount
            await self.bot.db.execute("UPDATE economy SET cash = cash - $1 WHERE user_id = $2", stolen_amount, member.id)
            await self.bot.db.execute("UPDATE economy SET cash = cash + $1 WHERE user_id = $2", real_stolen_amount, ctx.author.id)
            await self.bot.db.execute("UPDATE economy SET rob = $1 WHERE user_id = $2", int((datetime.datetime.now() + datetime.timedelta(hours=3)).timestamp()), ctx.author.id)
            await self.quests.add_collect_money(ctx.author, "rob", Decimal(real_stolen_amount))
            await self.economy.logging(ctx.author, Decimal(real_stolen_amount), "rob", f"<@{member.id}>")
            await self.economy.logging(member, Decimal(stolen_amount), "robbed", f"<@{ctx.author.id}>")
            return await ctx.send_success(f"You stole **{self.bot.misc.humanize_number(real_stolen_amount)}** {self.cash} from **{member.name}**")
        else:
            penalty = round(check["card"] * 0.05, 2)
            await self.bot.db.execute("UPDATE economy SET card = card - $1 WHERE user_id = $2", penalty, ctx.author.id)
            await self.bot.db.execute("UPDATE economy SET rob = $1 WHERE user_id = $2", int((datetime.datetime.now() + datetime.timedelta(hours=3)).timestamp()), ctx.author.id)
            await self.quests.add_collect_money(ctx.author, "rob", Decimal(0))
            await self.economy.logging(ctx.author, Decimal(penalty), "catched", f"<@{member.id}>")
            return await ctx.send_warning(f"Caught! You failed to steal from **{member.mention}** and lost **5%** (`{self.bot.misc.humanize_number(penalty)}`) of your **card** balance.")

    @command(name="daily", description="Claim your daily cash")
    @create_account()
    @daily_taken()
    @cooldown(1, 5, BucketType.user)
    async def daily(self, ctx: EvelinaContext):
        """Claim your daily cash"""
        check = await self.bot.db.fetchrow("SELECT cash, daily, daily_streak FROM economy WHERE user_id = $1", ctx.author.id)
        if not check:
            return await ctx.send("Error: User data not found.")
        now = datetime.datetime.utcnow()
        last_claim = datetime.datetime.utcfromtimestamp(check["daily"]) if check["daily"] else None
        daily_streak = check["daily_streak"] if last_claim and (now - last_claim).days < 2 else 1
        min_win = await self.bot.db.fetchval("SELECT daily_min FROM economy_config WHERE active = True")
        max_win = await self.bot.db.fetchval("SELECT daily_max FROM economy_config WHERE active = True")
        base_reward = random.uniform(min_win, max_win)
        total_bonus = await self.calculate_bonus(daily_streak, ctx.author.id)
        total_reward = base_reward * (1 + total_bonus / 100)
        await self.bot.db.execute("UPDATE economy SET cash = cash + $1, daily_streak = $2, daily = $3 WHERE user_id = $4", round(total_reward, 2), daily_streak, int((datetime.datetime.now() + datetime.timedelta(hours=24)).timestamp()), ctx.author.id)
        bonus_message = f"+{total_bonus}% Total Bonus" if total_bonus > 0 else ""
        await self.economy.logging(ctx.author, Decimal(total_reward), "collect", "daily")
        return await ctx.embed(f"You have claimed **{self.bot.misc.humanize_number(round(total_reward, 2))}** {self.cash} {bonus_message}", color=colors.SUCCESS, emoji=emojis.WIN)

    @command(aliases=["dstreak", "ds"], description="Get your daily streak with a calendar")
    @create_account()
    async def dailystreak(self, ctx: EvelinaContext, user: User = Author):
        """Get your daily streak with a calendar"""
        user_data = await self.bot.db.fetchrow("SELECT daily_streak FROM economy WHERE user_id = $1", user.id)
        if user_data is None or user_data['daily_streak'] is None:
            streak = 0
            return await ctx.send_warning(f"You don't have a daily streak, start one with **{ctx.clean_prefix}daily**")
        else:
            streak = user_data['daily_streak']
        total_percentage = await self.calculate_bonus(streak, user.id)
        today = datetime.datetime.now()
        start_of_streak = today - datetime.timedelta(days=streak - 1)
        embeds = []
        for month_offset in range(0, 12):
            target_month = (today.month - month_offset - 1) % 12 + 1
            target_year = today.year if target_month <= today.month else today.year - 1
            calendar_str = self.create_month_calendar(target_year, target_month, start_of_streak, today)
            embed = Embed(title=f"Your daily streak", color=colors.NEUTRAL)
            embed.description = f"**Streak:** {streak} day(s)\n**Bonus:** {total_percentage}%\n\n**Calendar:**\n**`{calendar.month_name[target_month]} {target_year}`**\n{calendar_str}"
            embed.set_author(name=user.name, icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            embeds.insert(1, embed)
        await ctx.paginator(embeds)

    @command(aliases=["cd"], usage="cooldowns comminate", description="Check the cooldowns for all economy commands")
    @create_account()
    async def cooldowns(self, ctx: EvelinaContext, member: Member = Author):
        """Check the cooldowns for all economy commands"""
        user_id = member.id
        beg_cd = await self.bot.db.fetchval("SELECT beg FROM economy WHERE user_id = $1", user_id)
        bonus_cd = await self.bot.db.fetchval("SELECT bonus FROM economy WHERE user_id = $1", user_id)
        work_cd = await self.bot.db.fetchval("SELECT work FROM economy WHERE user_id = $1", user_id)
        slut_cd = await self.bot.db.fetchval("SELECT slut FROM economy WHERE user_id = $1", user_id)
        rob_cd = await self.bot.db.fetchval("SELECT rob FROM economy WHERE user_id = $1", user_id)
        topgg_cd = await self.bot.db.fetchval("SELECT vote_until FROM votes WHERE user_id = $1", user_id)
        daily_cd = await self.bot.db.fetchval("SELECT daily FROM economy WHERE user_id = $1", user_id)
        def format_cd(cd, is_topgg=False):
            if cd is None:
                return "[`Available`](https://top.gg/bot/1242930981967757452/vote)" if is_topgg else "`Available`"
            now = datetime.datetime.utcnow()
            try:
                cd_time = datetime.datetime.utcfromtimestamp(int(cd))
            except ValueError:
                cd_time = datetime.datetime.strptime(cd, '%Y-%m-%d %H:%M:%S')
            if now > cd_time:
                return "[`Available`](https://top.gg/bot/1242930981967757452/vote)" if is_topgg else "`Available`"
            return f"<t:{int(cd_time.timestamp())}:R>"
        winnings = await self.bot.db.fetchrow("SELECT * FROM economy_config WHERE active = True")
        beg_amount = f"{self.bot.misc.humanize_clean_number(winnings['beg_min'])} - {self.bot.misc.humanize_clean_number(winnings['beg_max'])}"
        bonus_amount = f"{self.bot.misc.humanize_clean_number(winnings['bonus_min'])} - {self.bot.misc.humanize_clean_number(winnings['bonus_max'])}"
        work_amount = f"{self.bot.misc.humanize_clean_number(winnings['work_min'])} - {self.bot.misc.humanize_clean_number(winnings['work_max'])}"
        slut_amount = f"{self.bot.misc.humanize_clean_number(winnings['slut_min'])} - {self.bot.misc.humanize_clean_number(winnings['slut_max'])}"
        daily_amount = f"{self.bot.misc.humanize_clean_number(winnings['daily_min'])} - {self.bot.misc.humanize_clean_number(winnings['daily_max'])}"
        vote_amount = f"{self.bot.misc.humanize_clean_number(winnings['vote'])}"
        embed = Embed(color=colors.NEUTRAL)
        embed.add_field(name="Beg (1 Minute)", value=f"{format_cd(beg_cd)}\n{emojis.REPLY} {beg_amount} {self.cash}", inline=True)
        embed.add_field(name="Bonus (15 Minutes)", value=f"{format_cd(bonus_cd)}\n{emojis.REPLY} {bonus_amount} {self.cash}", inline=True)
        embed.add_field(name="Work (1 Hour)", value=f"{format_cd(work_cd)}\n{emojis.REPLY} {work_amount} {self.cash}", inline=True)
        embed.add_field(name="Slut (1 Hour)", value=f"{format_cd(slut_cd)}\n{emojis.REPLY} {slut_amount} {self.cash}", inline=True)
        embed.add_field(name="Rob (3 Hours)", value=f"{format_cd(rob_cd)}\n{emojis.REPLY} 10% from target {self.cash}", inline=True)
        embed.add_field(name="Vote (12 Hours)", value=f"{format_cd(topgg_cd, is_topgg=True)}\n{emojis.REPLY} {vote_amount} {self.cash}", inline=True)
        embed.add_field(name="Daily (24 Hours)", value=f"{format_cd(daily_cd)}\n{emojis.REPLY} {daily_amount} {self.cash}", inline=True)
        user_business = await self.economy.get_user_business(member.id)
        if user_business:
            system_business = await self.economy.get_system_business_by_id(user_business['business_id'])
            if await self.economy.calculate_business_earning(ctx.author.id, user_business['last_collected'], system_business['earnings']) <= 0:
                business_cd = user_business['last_collected'] + 3600
                business_earnings = system_business['earnings']
                _, _, _, multiplier = await self.economy.get_used_card(member.id, "business")
                if multiplier:
                    business_earnings = system_business['earnings'] * multiplier
                embed.add_field(name="Business (1 Hour)", value=f"{format_cd(business_cd)}\n{emojis.REPLY} {self.bot.misc.humanize_clean_number(business_earnings)} {self.cash}")
            else:
                embed.add_field(name="Business (1 Hour)", value=f"{format_cd(None)}\n{emojis.REPLY} {self.bot.misc.humanize_clean_number(system_business['earnings'])} {self.cash}")
        user_lab = await self.bot.db.fetchrow("SELECT * FROM economy_lab WHERE user_id = $1", ctx.author.id)
        if user_lab:
            if (int(time.time()) - user_lab["last_collected"]) < 3600:
                lab_cd = user_lab["last_collected"] + 3600
                earnings_per_hour, _, _ = await self.economy.calculate_lab_earnings_and_upgrade(ctx.author.id, user_lab['upgrade_state'])
                lab_earnings = earnings_per_hour
                embed.add_field(name="Lab (1 Hour)", value=f"{format_cd(lab_cd)}\n{emojis.REPLY} {self.bot.misc.humanize_clean_number(lab_earnings)} {self.cash}")
        embed.set_author(name=f"{member.name}'s cooldowns", icon_url=member.avatar.url if member.avatar else member.default_avatar.url)
        return await ctx.send(embed=embed)

    @command(name="economystats", aliases=["ecostats"], description="Get your economy stats")
    @create_account()
    async def economy_stats(self, ctx: EvelinaContext, member: Member = Author):
        """View your economy stats"""
        games = ["dice", "coinflip", "roulette", "blackjack", "ladder", "mines", "crash", "higherlower", "slots"]
        winnings = {}
        losses = {}
        for game in games:
            winnings[game] = await self.bot.db.fetchval(
                "SELECT COALESCE(SUM(amount), 0) FROM economy_logs WHERE user_id = $1 AND action = $2 AND type = $3",
                member.id, "won", game
            )
            losses[game] = await self.bot.db.fetchval(
                "SELECT COALESCE(SUM(amount), 0) FROM economy_logs WHERE user_id = $1 AND action = $2 AND type = $3",
                member.id, "lost", game
            )
        total_winnings = sum(winnings.values())
        total_losses = sum(losses.values())
        embed = Embed(color=colors.NEUTRAL, title=f"{member.name}'s Economy Stats")
        embed.description = f"**{emojis.ADD} Total Winnings:** {self.bot.misc.humanize_number(total_winnings)}\n**{emojis.REMOVE} Total Losses:** {self.bot.misc.humanize_number(total_losses)}"
        embed.set_author(name=member.name, icon_url=member.avatar.url if member.avatar else member.default_avatar.url)
        for game in games:
            embed.add_field(
                name=f"{game.capitalize()}",
                value=f"{emojis.ADD} {self.bot.misc.humanize_number(winnings[game])}\n"
                      f"{emojis.REMOVE} {self.bot.misc.humanize_number(losses[game])}",
                inline=True
            )
        return await ctx.send(embed=embed)

    @command(name="collectall", brief="donator")
    @create_account()
    async def collectall(self, ctx: EvelinaContext):
        """Collect all available earnings from your business, laboratory, daily, beg, bonus, work, slut, and company projects"""
        async with self.locks[ctx.author.id]:
            user_business = await self.economy.get_user_business(ctx.author.id)
            lab_info = await self.bot.db.fetchrow("SELECT * FROM economy_lab WHERE user_id = $1", ctx.author.id)
            user_data = await self.bot.db.fetchrow("SELECT * FROM economy WHERE user_id = $1", ctx.author.id)
            company = await self.economy.get_user_company(ctx.author.id)
            now = datetime.datetime.now()
            total_earnings = 0
            details = []
            if user_business:
                system_business = await self.economy.get_system_business_by_id(user_business['business_id'])
                business_earnings = await self.economy.calculate_business_earning(ctx.author.id, user_business['last_collected'], system_business['earnings'])
                if business_earnings > 0:
                    await self.bot.db.execute("UPDATE economy_business SET last_collected = $1 WHERE user_id = $2", datetime.datetime.now().timestamp(), ctx.author.id)
                    total_earnings += business_earnings
                    await self.quests.add_collect_money(ctx.author, "business", Decimal(business_earnings))
                    await self.economy.logging(ctx.author, Decimal(business_earnings), "collect", "business")
                    await self.economy.logging_business(ctx.author, self.bot.user, Decimal(business_earnings), "collect", system_business["business_id"])
                    details.append(f"- Business: **{self.bot.misc.humanize_number(business_earnings)}** {self.cash}")
            if lab_info:
                current_time = int(time.time())
                last_collected = lab_info["last_collected"]
                upgrade_state = lab_info["upgrade_state"]
                ampoules = lab_info["ampoules"]
                time_passed = current_time - last_collected
                collect = True
                if upgrade_state >= 16:
                    _, used_card_stars, _, _ = await self.economy.get_used_card(ctx.author.id, "lab")
                    if not used_card_stars:
                        collect = False
                        details.append(f"- Lab: **No card equipped**")
                    if used_card_stars:
                        if upgrade_state in range(16, 20):
                            if used_card_stars < 2:
                                collect = False
                                details.append(f"- Lab: **Card with 2 stars or more required**")
                        if upgrade_state in range(21, 30):
                            if used_card_stars < 3:
                                collect = False
                                details.append(f"- Lab: **Card with 3 stars or more required**")
                        if upgrade_state in range(31, 40):
                            if used_card_stars < 4:
                                collect = False
                                details.append(f"- Lab: **Card with 4 stars or more required**")
                        if upgrade_state in range(41, 50):
                            if used_card_stars < 5:
                                collect = False
                                details.append(f"- Lab: **Card with 5 stars or more required**")
                if time_passed >= 3600 and collect:
                    _, _, storage, _ = await self.economy.get_used_card(ctx.author.id, "lab")
                    if storage is None:
                        storage = 6
                    hours_passed = min(time_passed // 3600, int(storage))
                    _, _, used_card_storage, _ = await self.economy.get_used_card(ctx.author.id, "lab")
                    if used_card_storage:
                        if hours_passed > used_card_storage:
                            hours_passed = used_card_storage
                    ampoules_needed = hours_passed * 5
                    earnings_per_hour, earnings_cap, _ = await self.economy.calculate_lab_earnings_and_upgrade(ctx.author.id, upgrade_state)
                    lab_earnings = earnings_per_hour * hours_passed
                    if lab_earnings > earnings_cap:
                        lab_earnings = earnings_cap
                    earnings_12_hours = earnings_per_hour * 12
                    cost_for_100_ampoules = int(earnings_12_hours * 0.20)
                    ampoule_cost = cost_for_100_ampoules / 100
                    ampoules_to_buy = max(0, ampoules_needed - ampoules)
                    total_cost = int(ampoule_cost * ampoules_to_buy)
                    if ampoules_to_buy > 0 and lab_earnings >= total_cost:
                        lab_earnings -= total_cost
                        await self.bot.db.execute("UPDATE economy_lab SET ampoules = ampoules + $1 WHERE user_id = $2", ampoules_to_buy, ctx.author.id)
                        ampoules += ampoules_to_buy
                        details.append(f"- Purchased {ampoules_to_buy} ampoules for **{self.bot.misc.humanize_number(total_cost)}** {self.cash}")
                    if ampoules >= ampoules_needed:
                        total_earnings += lab_earnings
                        await self.bot.db.execute("UPDATE economy_lab SET last_collected = $1, ampoules = ampoules - $2 WHERE user_id = $3", current_time, ampoules_needed, ctx.author.id)
                        await self.quests.add_collect_money(ctx.author, "lab", Decimal(lab_earnings))
                        await self.economy.logging(ctx.author, Decimal(lab_earnings), "collect", "lab")
                        await self.economy.logging_lab(ctx.author, self.bot.user, Decimal(lab_earnings), "collect", lab_info["upgrade_state"])
                        details.append(f"- Lab: **{self.bot.misc.humanize_number(lab_earnings)}** {self.cash}")
            if user_data:
                if user_data['beg'] and now.timestamp() >= user_data['beg'] or user_data['beg'] == 0:
                    if not user_data['cash'] + user_data['card'] > 100000:
                        min_win = await self.bot.db.fetchval("SELECT beg_min FROM economy_config WHERE active = True")
                        max_win = await self.bot.db.fetchval("SELECT beg_max FROM economy_config WHERE active = True")
                        beg_earnings = random.uniform(min_win, max_win)
                        total_earnings += beg_earnings
                        details.append(f"- Beg: **{self.bot.misc.humanize_number(beg_earnings)}** {self.cash}")
                        await self.quests.add_collect_money(ctx.author, "beg", Decimal(beg_earnings))
                        await self.economy.logging(ctx.author, Decimal(beg_earnings), "collect", "beg")
                        await self.bot.db.execute("UPDATE economy SET beg = $1 WHERE user_id = $2", int((now + datetime.timedelta(minutes=1)).timestamp()), ctx.author.id)
                if user_data['bonus'] and now.timestamp() >= user_data['bonus'] or user_data['bonus'] == 0:
                    min_win = await self.bot.db.fetchval("SELECT bonus_min FROM economy_config WHERE active = True")
                    max_win = await self.bot.db.fetchval("SELECT bonus_max FROM economy_config WHERE active = True")
                    bonus_earnings = random.randint(min_win, max_win)
                    total_earnings += bonus_earnings
                    details.append(f"- Bonus: **{self.bot.misc.humanize_number(bonus_earnings)}** {self.cash}")
                    await self.quests.add_collect_money(ctx.author, "bonus", Decimal(bonus_earnings))
                    await self.economy.logging(ctx.author, Decimal(bonus_earnings), "collect", "bonus")
                    await self.bot.db.execute("UPDATE economy SET bonus = $1 WHERE user_id = $2", int((now + datetime.timedelta(minutes=15)).timestamp()), ctx.author.id)
                if user_data['work'] and now.timestamp() >= user_data['work'] or user_data['work'] == 0:
                    if company:
                        limit = await self.economy.get_level_info(company['level'])
                        work_earnings = limit['earnings']
                        total_earnings += work_earnings
                        details.append(f"- Work: **{self.bot.misc.humanize_number(work_earnings)}** {self.cash}")
                        await self.quests.add_collect_money(ctx.author, "work", Decimal(work_earnings))
                        await self.economy.logging(ctx.author, Decimal(work_earnings), "collect", "work")
                        await self.bot.db.execute("UPDATE economy SET work = $1 WHERE user_id = $2", int((datetime.datetime.now() + datetime.timedelta(hours=1)).timestamp()), ctx.author.id)
                    else:
                        min_win = await self.bot.db.fetchval("SELECT work_min FROM economy_config WHERE active = True")
                        max_win = await self.bot.db.fetchval("SELECT work_max FROM economy_config WHERE active = True")
                        work_earnings = round(random.uniform(min_win, max_win), 2)
                        total_earnings += work_earnings
                        details.append(f"- Work: **{self.bot.misc.humanize_number(work_earnings)}** {self.cash}")
                        await self.quests.add_collect_money(ctx.author, "work", Decimal(work_earnings))
                        await self.economy.logging(ctx.author, Decimal(work_earnings), "collect", "work")
                        await self.bot.db.execute("UPDATE economy SET work = $1 WHERE user_id = $2", int((now + datetime.timedelta(hours=1)).timestamp()), ctx.author.id)
                if user_data['slut'] and now.timestamp() >= user_data['slut'] or user_data['slut'] == 0:
                    min_win = await self.bot.db.fetchval("SELECT slut_min FROM economy_config WHERE active = True")
                    max_win = await self.bot.db.fetchval("SELECT slut_max FROM economy_config WHERE active = True")
                    slut_earnings = round(random.uniform(min_win, max_win), 2)
                    total_earnings += slut_earnings
                    details.append(f"- Slut: **{self.bot.misc.humanize_number(slut_earnings)}** {self.cash}")
                    await self.quests.add_collect_money(ctx.author, "slut", Decimal(slut_earnings))
                    await self.economy.logging(ctx.author, Decimal(slut_earnings), "collect", "slut")
                    await self.bot.db.execute("UPDATE economy SET slut = $1 WHERE user_id = $2", int((now + datetime.timedelta(hours=1)).timestamp()), ctx.author.id)
                last_daily_timestamp = user_data['daily'] if user_data['daily'] else 0
                daily_streak = user_data['daily_streak'] if user_data['daily_streak'] else 0
                last_daily_date = datetime.datetime.utcfromtimestamp(last_daily_timestamp) if last_daily_timestamp > 0 else None
                if last_daily_date:
                    days_since_last_claim = (now - last_daily_date).days
                    if days_since_last_claim < 2:
                        daily_streak += 1
                    else:
                        daily_streak = 1
                else:
                    daily_streak = 1
                if user_data['daily'] and now.timestamp() >= user_data['daily'] or user_data['daily'] == 0:
                    min_win = await self.bot.db.fetchval("SELECT daily_min FROM economy_config WHERE active = True")
                    max_win = await self.bot.db.fetchval("SELECT daily_max FROM economy_config WHERE active = True")
                    daily_earnings = round(random.uniform(min_win, max_win), 2)
                    total_bonus_percentage = await self.calculate_bonus(daily_streak, ctx.author.id)
                    daily_earnings *= (1 + total_bonus_percentage / 100)
                    total_earnings += daily_earnings
                    details.append(f"- Daily: **{self.bot.misc.humanize_number(daily_earnings)}** {self.cash} (+{total_bonus_percentage}% Bonus)")
                    await self.quests.add_collect_money(ctx.author, "daily", Decimal(daily_earnings))
                    await self.economy.logging(ctx.author, Decimal(daily_earnings), "collect", "daily")
                    await self.bot.db.execute("UPDATE economy SET daily = $1, daily_streak = $2 WHERE user_id = $3", int((now + datetime.timedelta(hours=24)).timestamp()), daily_streak, ctx.author.id)
            if company:
                earnings = await self.bot.db.fetchrow("SELECT * FROM company_earnings WHERE company_id = $1 AND user_id = $2", company['id'], ctx.author.id)
                if earnings and earnings['amount'] > 0:
                    amount = earnings['amount']
                    await self.bot.db.execute("UPDATE company_earnings SET amount = amount - $1 WHERE company_id = $2 AND user_id = $3", amount, company['id'], ctx.author.id)
                    await self.quests.add_collect_money(ctx.author, "company", Decimal(amount))
                    await self.economy.logging(ctx.author, Decimal(amount), "collect", "company")
                    total_earnings += amount
                    details.append(f"- Company Project: **{self.bot.misc.humanize_number(amount)}** {self.cash}")
            if total_earnings > 0:
                await self.bot.db.execute("UPDATE economy SET cash = cash + $1 WHERE user_id = $2", total_earnings, ctx.author.id)
                details_text = "\n".join(details)
                return await ctx.send_success(f"Successfully collected **{self.bot.misc.humanize_number(total_earnings)}** {self.cash}\n{details_text}")
            else:
                return await ctx.send_warning("No earnings available to collect.")
                
    @command(name="minigames", aliases=["games"], description="View all available economy games")
    @create_account()
    async def minigames(self, ctx: EvelinaContext):
        """View all available economy games"""
        embed = Embed(title="Economy Games", color=colors.NEUTRAL)
        embed.add_field(name="Dice", value=f"{emojis.REPLY} `{ctx.clean_prefix}dice`", inline=True)
        embed.add_field(name="Coinflip", value=f"{emojis.REPLY} `{ctx.clean_prefix}coinflip`", inline=True)
        embed.add_field(name="Roulette", value=f"{emojis.REPLY} `{ctx.clean_prefix}roulette`", inline=True)
        embed.add_field(name="Blackjack", value=f"{emojis.REPLY} `{ctx.clean_prefix}blackjack`", inline=True)
        embed.add_field(name="Ladder", value=f"{emojis.REPLY} `{ctx.clean_prefix}ladder`", inline=True)
        embed.add_field(name="Mines", value=f"{emojis.REPLY} `{ctx.clean_prefix}mines`", inline=True)
        embed.add_field(name="Crash", value=f"{emojis.REPLY} `{ctx.clean_prefix}crash`", inline=True)
        embed.add_field(name="HigherLower", value=f"{emojis.REPLY} `{ctx.clean_prefix}higherlower`", inline=True)
        embed.add_field(name="Slots", value=f"{emojis.REPLY} `{ctx.clean_prefix}slots`", inline=True)
        await ctx.send(embed=embed)

    @group(invoke_without_command=True, description="View your economy profile")
    @create_account()
    async def item(self, ctx: EvelinaContext):
        return await ctx.create_pages()

    @item.group(name="buy", invoke_without_command=True, description="Buy items for your account", case_insensitive=True)
    @create_account()
    async def item_buy(self, ctx: EvelinaContext):
        """Buy items for your account"""
        return await ctx.create_pages()

    @item_buy.command(name="bank", usage="item buy bank 10000", cooldown=5, description="Buy additional bank space")
    @create_account()
    @cooldown(1, 5, BucketType.user)
    async def item_buy_bank(self, ctx: EvelinaContext, amount: CashAmount):
        """Buy additional bank space"""
        user_data = await self.bot.db.fetchrow("SELECT cash, item_bank FROM economy WHERE user_id = $1", ctx.author.id)
        cost = amount * 1
        if user_data['cash'] < cost:
            return await ctx.send_warning(f"You don't have enough money to buy **{self.bot.misc.humanize_clean_number(amount)}** bank space.")
        new_bank_limit = user_data['item_bank'] + amount
        async def yes_callback(interaction: Interaction):
            user_data = await self.bot.db.fetchrow("SELECT cash, item_bank FROM economy WHERE user_id = $1", ctx.author.id)
            cost = amount * 1
            if user_data['cash'] < cost:
                return await interaction.response.edit_message(embed=Embed(description=f"{emojis.WARNING} {ctx.author.mention}: You don't have enough money to buy **{self.bot.misc.humanize_clean_number(amount)}** bank space.", color=colors.WARNING), view=None)
            await self.quests.add_deposit_money(ctx.author, "bank", Decimal(amount))
            await self.bot.db.execute("UPDATE economy SET cash = $1, item_bank = $2 WHERE user_id = $3", user_data['cash'] - cost, new_bank_limit, ctx.author.id)
            await self.economy.logging(ctx.author, Decimal(cost), "buy", "bank")
            await interaction.response.edit_message(embed=Embed(description=f"{emojis.APPROVE} {ctx.author.mention}: Successfully bought **{self.bot.misc.humanize_clean_number(amount)}** bank space for **{self.bot.misc.humanize_number(cost)}** {self.cash}", color=colors.SUCCESS), view=None)
        async def no_callback(interaction: Interaction):
            await interaction.response.edit_message(embed=Embed(description=f"{emojis.DENY} {ctx.author.mention}: Purchase got canceled", color=colors.ERROR), view=None)
        return await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to purchase **{amount:,.0f}** bank space for **{self.bot.misc.humanize_number(cost)}** {self.cash}?", yes_callback, no_callback)
    
    @item.group(name="sell", invoke_without_command=True, description="Sell items from your account", case_insensitive=True)
    @create_account()
    async def item_sell(self, ctx: EvelinaContext):
        """Sell items from your account"""
        return await ctx.create_pages()

    @item_sell.command(name="bank", usage="item sell bank 10000", cooldown=5, description="Sell bank space")
    @create_account()
    @cooldown(1, 5, BucketType.user)
    async def item_sell_bank(self, ctx: EvelinaContext, amount: BankAmount):
        """Sell bank space"""
        user_data = await self.bot.db.fetchrow("SELECT cash, item_bank, card FROM economy WHERE user_id = $1", ctx.author.id)
        if user_data['item_bank'] < amount:
            return await ctx.send_warning(f"You don't have **{self.bot.misc.humanize_number(amount)}** bank space to sell.")
        if user_data['item_bank'] - amount < user_data['card']:
            return await ctx.send_warning("You can't sell this much bank space.")
        sell_price = amount * 0.1
        new_bank_limit = user_data['item_bank'] - amount
        async def yes_callback(interaction: Interaction):
            user_data = await self.bot.db.fetchrow("SELECT cash, item_bank, card FROM economy WHERE user_id = $1", ctx.author.id)
            if user_data['item_bank'] < amount:
                return  await interaction.response.edit_message(embed=Embed(description=f"{emojis.WARNING} {ctx.author.mention}: You don't have **{self.bot.misc.humanize_number(amount)}** bank space to sell.", color=colors.WARNING), view=None)
            if user_data['item_bank'] - amount < user_data['card']:
                return  await interaction.response.edit_message(embed=Embed(description=f"{emojis.WARNING} {ctx.author.mention}: You can't sell this much bank space.", color=colors.WARNING), view=None)
            await self.bot.db.execute("UPDATE economy SET cash = $1, item_bank = $2 WHERE user_id = $3", user_data['cash'] + sell_price, new_bank_limit, ctx.author.id)
            await self.economy.logging(ctx.author, Decimal(sell_price), "sell", "bank")
            await interaction.response.edit_message(embed=Embed(description=f"{emojis.APPROVE} {ctx.author.mention}: Successfully sold **{self.bot.misc.humanize_number(amount)}** bank space for **{self.bot.misc.humanize_number(sell_price)}** {self.cash}", color=colors.SUCCESS), view=None)
        async def no_callback(interaction: Interaction):
            await interaction.response.edit_message(embed=Embed(description=f"{emojis.DENY} {ctx.author.mention}: Sale got canceled", color=colors.ERROR), view=None)
        return await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to sell **{amount:,.0f}** bank space for **{self.bot.misc.humanize_number(sell_price)}** {self.cash}?", yes_callback, no_callback)

    @group(name="card", aliases=["cards"], invoke_without_command=True, case_insensitive=True, description="View your economy cards")
    @create_account()
    async def card(self, ctx: EvelinaContext):
        """View your economy cards"""
        return await ctx.create_pages()

    @card.command(name="sell", usage="card sell 1 comminate 1000", cooldown=5, description="Sell a card from your account")
    @create_account()
    @cooldown(1, 5, BucketType.user)
    async def card_sell(self, ctx: EvelinaContext, card_id: int, member: Member, amount: Amount):
        """Sell a card from your account to another user"""
        user_data = await self.bot.db.fetchrow("SELECT cash FROM economy WHERE user_id = $1", ctx.author.id)
        card_data = await self.bot.db.fetchrow("SELECT * FROM economy_cards_user WHERE user_id = $1 AND card_id = $2 AND active = True", ctx.author.id, card_id)
        if not card_data:
            return await ctx.send_warning("You don't have this card.")
        card_info = await self.bot.db.fetchrow("SELECT * FROM economy_cards WHERE id = $1", card_data['id'])
        if not card_info:
            return await ctx.send_warning("This card does not exist.")
        if card_info['stars'] >= 5:
            limit = 100000000
        elif card_info['stars'] == 4:
            limit = 50000000
        elif card_info['stars'] == 3:
            limit = 25000000
        elif card_info['stars'] == 2:
            limit = 10000000
        elif card_info['stars'] == 1:
            limit = 5000000
        if amount > limit:
            return await ctx.send_warning(f"You can't sell this card for more than **{self.bot.misc.humanize_number(limit)}** {self.cash}.")
        member_data = await self.bot.db.fetchrow("SELECT cash FROM economy WHERE user_id = $1", member.id)
        if not member_data or member_data['cash'] < amount:
            return await ctx.send_warning(f"{member.mention} does not have enough money to buy this card.")
        async def yes_callback(interaction: Interaction):
            seller_card_data = await self.bot.db.fetchrow("SELECT * FROM economy_cards_user WHERE user_id = $1 AND card_id = $2", ctx.author.id, card_id)
            if not seller_card_data:
                return await interaction.response.edit_message(embed=Embed(description=f"{emojis.WARNING} {ctx.author.mention}: You don't have this card.", color=colors.WARNING), view=None)
            buyer_data = await self.bot.db.fetchrow("SELECT * FROM economy WHERE user_id = $1", member.id)
            if not buyer_data or buyer_data['cash'] < amount:
                return await interaction.response.edit_message(embed=Embed(description=f"{emojis.WARNING} {member.mention}: They don't have enough money.", color=colors.WARNING), view=None)
            await self.bot.db.execute("UPDATE economy_cards_user SET user_id = $1 WHERE user_id = $2 AND card_id = $3", interaction.user.id, ctx.author.id, card_id)
            await self.bot.db.execute("UPDATE economy SET cash = cash + $1 WHERE user_id = $2", (amount * 0.75), ctx.author.id)
            await self.bot.db.execute("UPDATE economy SET cash = cash - $1 WHERE user_id = $2", amount, member.id)
            await self.economy.logging(ctx.author, Decimal(amount * 0.75), "sell", "cards")
            await self.economy.logging(member, Decimal(amount), "buy", "cards")
            await interaction.response.edit_message(embed=Embed(description=f"{emojis.APPROVE} {ctx.author.mention}: Successfully sold the card to {member.mention} for **{self.bot.misc.humanize_number(amount)}** {self.cash} (`{self.bot.misc.humanize_number(amount * 0.75)}`).", color=colors.SUCCESS), view=None)
        async def no_callback(interaction: Interaction):
            await interaction.response.edit_message(embed=Embed(description=f"{emojis.DENY} {ctx.author.mention}: Sale got canceled", color=colors.ERROR), view=None)
        confirm_view = ConfirmView(ctx, self.bot, card_id, 1, amount, yes_callback, no_callback, member)
        return await ctx.send(embed=Embed(description=f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to sell this card to {member.mention} for **{self.bot.misc.humanize_number(amount)}** {self.cash}?", color=colors.NEUTRAL), view=confirm_view)

    @card.command(name="trade", usage="card trade 1 2 comminate", cooldown=5, description="Trade a card with another user")
    @create_account()
    @cooldown(1, 5, BucketType.user)
    async def card_trade(self, ctx: EvelinaContext, card_id: int, target_card_id: int, member: Member):
        """Trade a card with another user"""
        card_data = await self.bot.db.fetchrow("SELECT * FROM economy_cards_user WHERE user_id = $1 AND card_id = $2 AND active = True", ctx.author.id, card_id)
        if not card_data:
            return await ctx.send_warning("You don't have this card.")
        target_card_data = await self.bot.db.fetchrow("SELECT * FROM economy_cards_user WHERE user_id = $1 AND card_id = $2 AND active = True", member.id, target_card_id)
        if not target_card_data:
            return await ctx.send_warning(f"{member.mention} doesn't have this card.")
        card_info = await self.bot.db.fetchrow("SELECT * FROM economy_cards WHERE id = $1", card_data['id'])
        target_card_info = await self.bot.db.fetchrow("SELECT * FROM economy_cards WHERE id = $1", target_card_data['id'])
        async def yes_callback(interaction: Interaction):
            card_data = await self.bot.db.fetchrow("SELECT * FROM economy_cards_user WHERE user_id = $1 AND card_id = $2", ctx.author.id, card_id)
            target_card_data = await self.bot.db.fetchrow("SELECT * FROM economy_cards_user WHERE user_id = $1 AND card_id = $2", member.id, target_card_id)
            if not card_data:
                return await interaction.response.edit_message(embed=Embed(description=f"{emojis.WARNING} {ctx.author.mention}: You don't have this card.", color=colors.WARNING), view=None)
            if not target_card_data:
                return await interaction.response.edit_message(embed=Embed(description=f"{emojis.WARNING} {member.mention}: They don't have this card.", color=colors.WARNING), view=None)
            await self.bot.db.execute("UPDATE economy_cards_user SET user_id = $1 WHERE user_id = $2 AND card_id = $3", interaction.user.id, ctx.author.id, card_id)
            await self.bot.db.execute("UPDATE economy_cards_user SET user_id = $1 WHERE user_id = $2 AND card_id = $3", ctx.author.id, member.id, target_card_id)
            await interaction.response.edit_message(embed=Embed(description=f"{emojis.APPROVE} {ctx.author.mention}: Successfully traded the card with {member.mention}", color=colors.SUCCESS), view=None)
        async def no_callback(interaction: Interaction):
            await interaction.response.edit_message(embed=Embed(description=f"{emojis.DENY} {ctx.author.mention}: Trade got canceled", color=colors.ERROR), view=None)
        return await ctx.target_confirmation_send(f"{emojis.QUESTION} {member.mention}: Are you sure you want to trade these cards with {ctx.author.mention}?\n> {ctx.author.mention}: {card_info['name']} (`{card_info['stars']}`)\n> {member.mention}: {target_card_info['name']} (`{target_card_info['stars']}`)", member.id, yes_callback, no_callback)

    @card.command(name="upgrade", usage="card upgrade 1 manager", description="Upgrade your cards")
    @create_account()
    async def card_upgrade(self, ctx: EvelinaContext, stars: int, type: str):
        """Upgrade your cards"""
        if stars not in [2, 3, 4]:
            return await ctx.send_warning("Invalid stars, please choose between `2`, `3` & `4`.")
        if type not in ["manager", "scientist", "security"]:
            return await ctx.send_warning("Invalid type, please choose between `manager`, `scientist` & `security`.")
        if stars == 2:
            await self.economy.upgrade_cards_for_stars(ctx, type, (9, 11), (1.3, 1.5), (55, 64), "⭐⭐", 2)
        elif stars == 3:
            await self.economy.upgrade_cards_for_stars(ctx, type, (12, 16), (1.6, 1.9), (65, 74), "⭐⭐⭐", 3)
        elif stars == 4:
            await self.economy.upgrade_cards_for_stars(ctx, type, (18, 22), (2.0, 2.4), (75, 84), "⭐⭐⭐⭐", 4)

    @card.command(name="shred", usage="card shred stars 5 10", description="Shred cards to gain money, type is either `stars` or `id`")
    @create_account()
    async def card_shred(self, ctx: EvelinaContext, type: str, id: int, amount: int):
        """Shred cards to gain money"""
        msg = await ctx.send_loading("Opening cases...")
        if type not in ["stars", "id"]:
            return await ctx.send_warning("Invalid type, please choose between `stars` & `id`.", obj=msg)
        if amount < 1:
            return await ctx.send_warning("You need to shred at least 1 card.", obj=msg)
        if type == "stars":
            if id not in [1, 2, 3, 4, 5]:
                return await ctx.send_warning("Invalid stars, please choose between `1`, `2`, `3`, `4` & `5`.", obj=msg)
            user_cards = await self.bot.db.fetch("SELECT * FROM economy_cards_user WHERE user_id = $1 AND active = TRUE", ctx.author.id)
            if not user_cards:
                return await ctx.send_warning("You don't have any cards.", obj=msg)
            card_defs = await self.bot.db.fetch("SELECT id FROM economy_cards WHERE stars = $1", id)
            valid_card_ids = {c['id'] for c in card_defs}
            matching_cards = [card for card in user_cards if card['id'] in valid_card_ids]
            if len(matching_cards) < amount:
                return await ctx.send_warning(f"You don't have enough cards with **{id}** stars.", obj=msg)
            prices = {
                "standard": {1: 350000, 2: 750000, 3: 1250000, 4: 3500000, 5: 50000000},
                "blackice": {1: 1750000, 2: 3750000, 3: 6250000, 4: 17500000, 5: 250000000}
            }
            earnings = 0
            to_delete_ids = []
            for card in matching_cards[:amount]:
                background = card['background']
                earnings += prices.get(background, {}).get(id, 0)
                to_delete_ids.append(card['card_id'])
            await self.bot.db.execute("DELETE FROM economy_cards_user WHERE user_id = $1 AND card_id = ANY($2::bigint[])", ctx.author.id, to_delete_ids)
            await self.bot.db.execute("UPDATE economy SET cash = cash + $1 WHERE user_id = $2", earnings, ctx.author.id)
            await self.economy.logging(ctx.author, Decimal(earnings), "shred", "cards")
            return await ctx.send_success(f"Successfully shredded **{amount}** cards with **{id}** stars for **{self.bot.misc.humanize_number(earnings)}** {self.cash}.", obj=msg)
        elif type == "id":
            card_entries = await self.bot.db.fetch("SELECT * FROM economy_cards_user WHERE user_id = $1 AND active = TRUE AND card_id = $2", ctx.author.id, id)
            if not card_entries or len(card_entries) < amount:
                return await ctx.send_warning(f"You don't have enough cards with ID **{id}**.", obj=msg)
            card_info = await self.bot.db.fetchrow("SELECT stars FROM economy_cards WHERE id = (SELECT id FROM economy_cards_user WHERE card_id = $1 LIMIT 1)", id)
            background = await self.bot.db.fetchval("SELECT background FROM economy_cards_user WHERE card_id = $1", id)
            if not card_info:
                return await ctx.send_warning("This card does not exist.", obj=msg)
            stars = card_info['stars']
            prices = {
                "standard": {1: 350000, 2: 750000, 3: 1250000, 4: 3500000, 5: 50000000},
                "blackice": {1: 1750000, 2: 3750000, 3: 6250000, 4: 17500000, 5: 250000000}
            }
            earnings = prices.get(background, {}).get(stars, 0) * amount
            to_delete_ids = [entry['card_id'] for entry in card_entries[:amount]]
            await self.bot.db.execute("DELETE FROM economy_cards_user WHERE user_id = $1 AND card_id = ANY($2::bigint[])", ctx.author.id, to_delete_ids)
            await self.bot.db.execute("UPDATE economy SET cash = cash + $1 WHERE user_id = $2", earnings, ctx.author.id)
            await self.economy.logging(ctx.author, Decimal(earnings), "shred", "cards")
            return await ctx.send_success(f"Successfully shredded **{amount}** cards with **ID {id}** for **{self.bot.misc.humanize_number(earnings)}** {self.cash}.", obj=msg)
    
    @card.command(name="use", usage="card use 1", description="Use a card from your account")
    @create_account()
    async def card_use(self, ctx: EvelinaContext, card_id: int):
        """Use a card from your account"""
        card_data = await self.bot.db.fetchrow("SELECT * FROM economy_cards_user WHERE user_id = $1 AND card_id = $2", ctx.author.id, card_id)
        if not card_data:
            return await ctx.send_warning("You don't have this card.")
        card_info = await self.bot.db.fetchrow("SELECT * FROM economy_cards WHERE id = $1", card_data['id'])
        if not card_info:
            return await ctx.send_warning("This card does not exist.")
        if card_info['business'] == "business":
            business = await self.economy.get_user_business(ctx.author.id)
            if not business:
                return await ctx.send_warning("You don't have a business.")
            check = await self.bot.db.fetchrow("SELECT * FROM economy_cards_used WHERE user_id = $1 AND card_id = $2", ctx.author.id, card_id)
            if check:
                return await ctx.send_warning("You already used this card.")
            check_2 = await self.bot.db.fetchrow("SELECT * FROM economy_cards_used WHERE user_id = $1", ctx.author.id)
            if check_2 and check_2['business'] == "business":
                return await ctx.send_warning("You already used a business card.")
            await self.bot.db.execute("UPDATE economy_cards_user SET active = False WHERE user_id = $1 AND card_id = $2", ctx.author.id, card_id)
            await self.bot.db.execute("INSERT INTO economy_cards_used (user_id, card_id, business) VALUES ($1, $2, $3)", ctx.author.id, card_id, "business")
            return await ctx.send_success(f"Successfully used the **{card_info['name']}** card on your business.")
        elif card_info['business'] == "lab":
            lab = await self.bot.db.fetchrow("SELECT * FROM economy_lab WHERE user_id = $1", ctx.author.id)
            if not lab:
                return await ctx.send_warning("You don't have a lab.")
            check = await self.bot.db.fetchrow("SELECT * FROM economy_cards_used WHERE user_id = $1 AND card_id = $2", ctx.author.id, card_id)
            if check:
                return await ctx.send_warning("You already used this card.")
            check_2 = await self.bot.db.fetchrow("SELECT * FROM economy_cards_used WHERE user_id = $1", ctx.author.id)
            if check_2 and check_2['business'] == "lab":
                return await ctx.send_warning("You already used a lab card.")
            await self.bot.db.execute("UPDATE economy_cards_user SET active = False WHERE user_id = $1 AND card_id = $2", ctx.author.id, card_id)
            await self.bot.db.execute("INSERT INTO economy_cards_used (user_id, card_id, business) VALUES ($1, $2, $3)", ctx.author.id, card_id, "lab")
            return await ctx.send_success(f"Successfully used the **{card_info['name']}** card on your lab.")
        elif card_info['business'] == "personal":
            check = await self.bot.db.fetchrow("SELECT * FROM economy_cards_used WHERE user_id = $1 AND card_id = $2", ctx.author.id, card_id)
            if check:
                return await ctx.send_warning("You already used this card.")
            check_2 = await self.bot.db.fetchrow("SELECT * FROM economy_cards_used WHERE user_id = $1", ctx.author.id)
            if check_2 and check_2['business'] == "personal":
                return await ctx.send_warning("You already used a personal card.")
            await self.bot.db.execute("UPDATE economy_cards_user SET active = False WHERE user_id = $1 AND card_id = $2", ctx.author.id, card_id)
            await self.bot.db.execute("INSERT INTO economy_cards_used (user_id, card_id, business) VALUES ($1, $2, $3)", ctx.author.id, card_id, "personal")
            return await ctx.send_success(f"Successfully used the **{card_info['name']}** card.")
        else:
            return await ctx.send_warning("This card can't be used on anything.")
        
    @card.command(name="unuse", usage="card unuse 1", description="Unuse a card from your account")
    @create_account()
    async def card_unuse(self, ctx: EvelinaContext, card_id: int):
        """Unuse a card from your account"""
        card_data = await self.bot.db.fetchrow("SELECT * FROM economy_cards_user WHERE user_id = $1 AND card_id = $2", ctx.author.id, card_id)
        if not card_data:
            return await ctx.send_warning("You don't have this card.")
        card_info = await self.bot.db.fetchrow("SELECT * FROM economy_cards WHERE id = $1", card_data['id'])
        if not card_info:
            return await ctx.send_warning("This card does not exist.")
        if card_info['business'] == "business":
            check = await self.bot.db.fetchrow("SELECT * FROM economy_cards_used WHERE user_id = $1 AND card_id = $2", ctx.author.id, card_id)
            if not check:
                return await ctx.send_warning("You didn't use this card.")
            if check and check['business'] != "business":
                return await ctx.send_warning("You didn't use this card on your business.")
            await self.bot.db.execute("UPDATE economy_cards_user SET active = True WHERE user_id = $1 AND card_id = $2", ctx.author.id, card_id)
            await self.bot.db.execute("DELETE FROM economy_cards_used WHERE user_id = $1 AND card_id = $2", ctx.author.id, card_id)
            return await ctx.send_success(f"Successfully unused the **{card_info['name']}** card from your business.")
        elif card_info['business'] == "lab":
            check = await self.bot.db.fetchrow("SELECT * FROM economy_cards_used WHERE user_id = $1 AND card_id = $2", ctx.author.id, card_id)
            if not check:
                return await ctx.send_warning("You didn't use this card.")
            if check and check['business'] != "lab":
                return await ctx.send_warning("You didn't use this card on your lab.")
            await self.bot.db.execute("UPDATE economy_cards_user SET active = True WHERE user_id = $1 AND card_id = $2", ctx.author.id, card_id)
            await self.bot.db.execute("DELETE FROM economy_cards_used WHERE user_id = $1 AND card_id = $2", ctx.author.id, card_id)
            return await ctx.send_success(f"Successfully unused the **{card_info['name']}** card from your lab.")
        elif card_info['business'] == "personal":
            check = await self.bot.db.fetchrow("SELECT * FROM economy_cards_used WHERE user_id = $1 AND card_id = $2", ctx.author.id, card_id)
            if not check:
                return await ctx.send_warning("You didn't use this card.")
            if check and check['business'] != "personal":
                return await ctx.send_warning("You didn't use this card on your personal.")
            await self.bot.db.execute("UPDATE economy_cards_user SET active = True WHERE user_id = $1 AND card_id = $2", ctx.author.id, card_id)
            await self.bot.db.execute("DELETE FROM economy_cards_used WHERE user_id = $1 AND card_id = $2", ctx.author.id, card_id)
            return await ctx.send_success(f"Successfully unused the **{card_info['name']}** card.")
        else:
            return await ctx.send_warning("This card can't be unused.")

    @card.command(name="used", description="View all your used cards")
    @create_account()
    async def card_used(self, ctx: EvelinaContext, user: User = Author):
        """View all your used cards"""
        card_data = await self.bot.db.fetch("SELECT * FROM economy_cards_used WHERE user_id = $1", user.id)
        if not card_data:
            return await ctx.send_warning("You don't have any used cards.")
        embeds = []
        for card in card_data:
            card_user = await self.bot.db.fetchrow("SELECT * FROM economy_cards_user WHERE card_id = $1", card['card_id'])
            card_info = await self.bot.db.fetchrow("SELECT * FROM economy_cards WHERE id = $1", card_user['id'])
            item_rarity = card_info['stars']
            item_stars = "⭐" * item_rarity
            item_name = card_info['name']
            item_file = card_user['image']
            embed = Embed(title=f"{item_name} | {item_stars}", color=colors.NEUTRAL)
            embed.set_author(name=user.name, icon_url=user.avatar.url if user.avatar else user.default_avatar.url)
            embed.set_image(url=item_file)
            embed.set_footer(text=f"Page: {len(embeds) + 1}/{len(card_data)} ({len(card_data)} entries)")
            embeds.append(embed)
        return await ctx.paginator(embeds)

    @card.command(name="list", aliases=["view"], usage="card list comminate", description="View all your active cards with filters and pagination")
    @create_account()
    async def card_list(self, ctx: EvelinaContext, *, user: User = Author):
        """Displays all **active** cards with pagination and filters for business type, multiplier, and storage sorting."""
        await ctx.defer()
        card_data = await self.bot.db.fetch("SELECT * FROM economy_cards_user WHERE user_id = $1 AND active = True", user.id)
        if not card_data:
            return await ctx.send_warning(f"{user.mention} has no active cards.")
        view = CardListView(ctx, card_data)
        await view.populate_embeds()
        await ctx.send(embed=view.embeds[0] if view.embeds else Embed(description=f"{emojis.WARNING} {ctx.author.mention}: No cards found", color=colors.WARNING), view=view)

    @card.group(name="case", invoke_without_command=True, case_insensitive=True, description="View your economy cases")
    @create_account()
    async def card_case(self, ctx: EvelinaContext):
        """View your economy cases"""
        return await ctx.create_pages()
    
    @card_case.command(name="buy", usage="card case buy standard 10", cooldown=5, description="Buy a case to get a random item")
    @create_account()
    @cooldown(1, 5, BucketType.user)
    async def card_case_buy(self, ctx: EvelinaContext, type: str, amount: Amount):
        """Buy a case to get a random item"""
        type = type.lower()
        if type not in ["standard","blackice"]:
            return await ctx.send_warning("Invalid type. Please choose between `standard` & `blackice`.")
        cost_per_case = 1000000 if type == "standard" else 5000000 if type == "blackice" else 0
        user_data = await self.bot.db.fetchrow("SELECT cash, item_case FROM economy WHERE user_id = $1", ctx.author.id)
        cost = amount * cost_per_case
        if user_data['cash'] < cost:
            return await ctx.send_warning(f"You don't have enough money to buy **{self.bot.misc.humanize_clean_number(amount)}** {type} cases.\n> You need **{self.bot.misc.humanize_number(cost)}** {self.cash}.")
        async def yes_callback(interaction: Interaction):
            user_data = await self.bot.db.fetchrow("SELECT cash, item_case FROM economy WHERE user_id = $1", ctx.author.id)
            cost = amount * cost_per_case
            if user_data['cash'] < cost:
                return await interaction.response.edit_message(embed=Embed(description=f"{emojis.WARNING} {ctx.author.mention}: You don't have enough money to buy **{self.bot.misc.humanize_clean_number(amount)}** {type} cases.", color=colors.WARNING), view=None)
            column = "item_case" if type == "standard" else "item_case_blackice" if type == "blackice" else None
            await self.bot.db.execute(f"UPDATE economy SET cash = $1, {column} = {column} + $2 WHERE user_id = $3", user_data['cash'] - cost, amount, ctx.author.id)
            await self.economy.logging(ctx.author, Decimal(cost), "buy", f"{type} cases")
            await interaction.response.edit_message(embed=Embed(description=f"{emojis.APPROVE} {ctx.author.mention}: Successfully bought **{self.bot.misc.humanize_clean_number(amount)}** {type} cases for **{self.bot.misc.humanize_number(cost)}** {self.cash}", color=colors.SUCCESS), view=None)
        async def no_callback(interaction: Interaction):
            await interaction.response.edit_message(embed=Embed(description=f"{emojis.DENY} {ctx.author.mention}: Purchase got canceled", color=colors.ERROR), view=None)
        return await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to purchase **{self.bot.misc.humanize_clean_number(amount)}** {type} cases for **{self.bot.misc.humanize_number(cost)}** {self.cash}?", yes_callback, no_callback)

    @card_case.command(name="open", usage="card case open standard manager 3", cooldown=5, description="Open cases to get random items")
    @create_account()
    @cooldown(1, 10, BucketType.user)
    async def card_case_open(self, ctx: EvelinaContext, case: str, type: str, amount: int):
        """Open cases to get random items"""
        msg = await ctx.send_loading("Opening cases...")
        if case not in ["standard", "blackice"]:
            return await ctx.send_warning("Invalid case type, please choose between `standard` & `blackice`.", obj=msg)
        if type not in ["manager", "scientist", "security"]:
            return await ctx.send_warning("Invalid type, please choose between `manager`, `scientist` & `security`.", obj=msg)
        if amount < 1 or amount > 10:
            return await ctx.send_warning("You can only open between 1 and 10 cases at a time.", obj=msg)
        user_data = await self.bot.db.fetchrow("SELECT * FROM economy WHERE user_id = $1", ctx.author.id)
        column = "item_case" if case == "standard" else "item_case_blackice" if case == "blackice" else None
        if user_data[column] < amount:
            return await ctx.send_warning(f"You don't have enough {case} cases to use", obj=msg)
        items = []
        async with self.lock:
            tasks = []
            for _ in range(amount):
                if case == "standard":
                    chance_5 = 0.25
                    chance_4 = 0.75
                    chance_3 = 4.25
                    chance_2 = 15.00
                    background = "standard"
                elif case == "blackice":
                    chance_5 = 1.00
                    chance_4 = 2.00
                    chance_3 = 7.00
                    chance_2 = 90.00
                    background = "blackice"
                tasks.append(self.open_case(ctx, type, chance_5, chance_4, chance_3, chance_2, background))
            results = await asyncio.gather(*tasks)
            for result in results:
                if result['error']:
                    return await ctx.send_warning(result['message'], obj=msg)
                items.append(result['embed'])
            await self.bot.db.execute(f"UPDATE economy SET {column} = {column} - $1 WHERE user_id = $2", amount, ctx.author.id)
            await msg.delete()
            summary_embed = Embed(title="Summary", color=colors.NEUTRAL)
            summary_embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            for result in results:
                card_user_info = await self.bot.db.fetchrow("SELECT * FROM economy_cards_user WHERE card_id = $1", result['card_id'])
                card_info = await self.bot.db.fetchrow("SELECT * FROM economy_cards WHERE id = $1", card_user_info['id'])
                if card_info and card_user_info:
                    summary_embed.add_field(
                        name=f"{card_info['name']} | {'⭐' * card_info['stars']}",
                        value=f"Storage: {card_user_info['storage']}h\nMultiplier: {card_user_info['multiplier']}x",
                        inline=True
                    )
            items.insert(0, summary_embed)
            return await ctx.paginator(items)
        
    @card.command(name="generate", usage="card generate comminate 1000 pink", cooldown=5, description="Generate a card")
    @create_account()
    @is_manager()
    @cooldown(1, 10, BucketType.user)
    async def card_generate(self, ctx: EvelinaContext, user: User, card_id: int, type: str):
        """Generate a card"""
        if type not in ["pink", "standard", "blackice", "gold"]:
            return await ctx.send_warning("Invalid type, please choose between `gold`, `pink`, `blackice` & `standard`.")
        item_data = await self.bot.db.fetchrow("SELECT * FROM economy_cards WHERE id = $1", card_id)
        if not item_data:
            return await ctx.send_warning("This card does not exist.")
        item_rarity = item_data['stars']
        if item_data['business'] == "business":
            item_storage = 30
            item_multiplication = 3.5
        elif item_data['business'] == "lab":
            item_storage = 30
            item_multiplication = 3.5
        elif item_data['business'] == "personal":
            item_storage = 100
            item_multiplication = 3.5
        if item_data['business'] == "personal":
            item_storage_formated = f"{item_storage}%"
        else:
            item_storage_formated = f"{item_storage}h"
        item_multiplication_formated = f"{round(item_multiplication, 2)}x"
        while True:
            item_id = random.randint(100000, 999999)
            check_if_item_card_exists = await self.bot.db.fetchrow("SELECT * FROM economy_cards_user WHERE card_id = $1", item_id)
            if not check_if_item_card_exists:
                break
        item_name = item_data['name']
        item_data_business = str(item_data['business']).replace("business", "manager").replace("lab", "scientist").replace("personal", "security")
        item_card = await self.economy.create_id_card(item_data_business, item_id, item_storage_formated, item_multiplication_formated, item_name, item_rarity, item_data['image'], type)
        file_data = item_card.getvalue()
        file_code = f"{str(uuid.uuid4())[:8]}"
        file_name = f"{file_code}.png"
        content_type = "image/png"
        upload_res = await self.bot.r2.upload_file("evelina", file_data, file_name, content_type, "card")
        if upload_res:
            file_url = f"https://cdn.evelina.bot/card/{file_name}"
        else:
            return await ctx.send_warning("Failed to upload the card image.")
        await self.bot.db.execute("INSERT INTO economy_cards_user (id, user_id, card_id, business, storage, multiplier, image, background) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)", item_data['id'], user.id, item_id, item_data['business'], item_storage, item_multiplication, file_url, type)
        embed = Embed(title=f"{item_name} | {'⭐' * item_rarity}", color=colors.NEUTRAL)
        embed.set_author(name=user.name, icon_url=user.avatar.url if user.avatar else user.default_avatar.url)
        embed.set_image(url=file_url)
        embed.add_field(name="Card ID", value=item_id, inline=True)
        embed.add_field(name="Storage", value=item_storage_formated, inline=True)
        embed.add_field(name="Multiplier", value=item_multiplication_formated, inline=True)
        return await ctx.send(embed=embed)

    async def open_case(self, ctx: EvelinaContext, type: str, chance_5: float, chance_4: float, chance_3: float, chance_2: float, background: str):
        random_number_1 = random.uniform(0, 100)
        if random_number_1 <= chance_5:
            item_rarity = 5
            if type == "security":
                item_storage = random.randint(85, 90)
            else:
                if background == "standard":
                    item_storage = random.randint(24, 27)
                elif background == "blackice":
                    item_storage = random.randint(48, 54)
            item_multiplication = round(random.uniform(2.5, 3.0), 1)
        elif random_number_1 <= chance_5 + chance_4:
            item_rarity = 4
            if type == "security":
                item_storage = random.randint(75, 84)
            else:
                if background == "standard":
                    item_storage = random.randint(18, 22)
                elif background == "blackice":
                    item_storage = random.randint(36, 44)
            item_multiplication = round(random.uniform(2.0, 2.4), 1)
        elif random_number_1 <= chance_5 + chance_4 + chance_3:
            item_rarity = 3
            if type == "security":
                item_storage = random.randint(65, 74)
            else:
                if background == "standard":
                    item_storage = random.randint(12, 16)
                elif background == "blackice":
                    item_storage = random.randint(24, 32)
            item_multiplication = round(random.uniform(1.6, 1.9), 1)
        elif random_number_1 <= chance_5 + chance_4 + chance_3 + chance_2:
            item_rarity = 2
            if type == "security":
                item_storage = random.randint(55, 64)
            else:
                if background == "standard":
                    item_storage = random.randint(9, 11)
                elif background == "blackice":
                    item_storage = random.randint(18, 22)
            item_multiplication = round(random.uniform(1.3, 1.5), 1)
        else:
            item_rarity = 1
            if type == "security":
                item_storage = random.randint(50, 54)
            else:
                if background == "standard":
                    item_storage = random.randint(6, 8)
                elif background == "blackice":
                    item_storage = random.randint(12, 16)
            item_multiplication = round(random.uniform(1.1, 1.2), 1)
        item_business = type.replace("manager", "business").replace("scientist", "lab").replace("security", "personal")
        item_data = await self.bot.db.fetchrow("SELECT * FROM economy_cards WHERE stars = $1 AND business = $2 ORDER BY RANDOM() LIMIT 1", item_rarity, item_business)
        if not item_data:
            return {'error': True, 'message': f"Failed to find a {item_business} card with {item_rarity} stars."}
        item_rarity = item_rarity
        item_stars = "⭐" * item_rarity
        if type == "security":
            item_storage_formated = f"{item_storage}%"
        else:
            item_storage_formated = f"{item_storage}h"
        item_multiplication_formated = f"{round(item_multiplication, 2)}x"
        while True:
            item_id = random.randint(100000, 999999)
            check_if_item_card_exists = await self.bot.db.fetchrow("SELECT * FROM economy_cards_user WHERE card_id = $1", item_id)
            if not check_if_item_card_exists:
                break
        item_name = item_data['name']
        item_card = await self.economy.create_id_card(type, item_id, item_storage_formated, item_multiplication_formated, item_name, item_rarity, item_data['image'], background)
        file_data = item_card.getvalue()
        file_code = f"{str(uuid.uuid4())[:8]}"
        file_name = f"{file_code}.png"
        content_type = "image/png"
        upload_res = await self.bot.r2.upload_file("evelina", file_data, file_name, content_type, "card")
        if upload_res:
            file_url = f"https://cdn.evelina.bot/card/{file_name}"
        else:
            return {'error': True, 'message': "Failed to upload the card image."}
        await self.bot.db.execute("INSERT INTO economy_cards_user (id, user_id, card_id, business, storage, multiplier, image, background) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)", item_data['id'], ctx.author.id, item_id, item_business.lower(), item_storage, item_multiplication, file_url, background)
        embed = Embed(title=f"{item_name} | {item_stars}", color=colors.NEUTRAL)
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed.set_image(url=file_url)
        embed.add_field(name="Card ID", value=item_id, inline=True)
        embed.add_field(name="Storage", value=item_storage_formated, inline=True)
        embed.add_field(name="Multiplier", value=item_multiplication_formated, inline=True)
        return {'error': False, 'embed': embed, 'rarity': item_rarity, 'card_id': item_id}

    @command(name="inventory", aliases=["inv"], description="View your inventory")
    @create_account()
    async def inventory(self, ctx: EvelinaContext, user: User = Author):
        """View your inventory or from a given user"""
        user_data = await self.bot.db.fetchrow("SELECT * FROM economy WHERE user_id = $1", user.id)
        if user_data is None:
            return await ctx.send("Error: User data not found.")
        embed = Embed(color=colors.NEUTRAL)
        embed.set_author(name=f"{user.name}'s Inventory", icon_url=user.avatar.url if user.avatar else user.default_avatar.url)
        embed.add_field(name="Bank Space", value=f"{user_data['item_bank']:,.0f}", inline=True)
        embed.add_field(name="Cases", value=f"{user_data['item_case']:,.0f}", inline=True)
        embed.add_field(name="Blackice Cases", value=f"{user_data['item_case_blackice']:,.0f}", inline=True)
        return await ctx.send(embed=embed)

    @group(aliases=["b"], invoke_without_command=True, description="Manage your business")
    @create_account()
    async def business(self, ctx: EvelinaContext):
        """Manage your business"""
        return await ctx.create_pages()

    @business.command(name="buy", usage="business buy Warehouse", description="Buy a business")
    @create_account()
    async def business_buy(self, ctx: EvelinaContext, *, business: str):
        """Buy a business"""
        async with self.locks[ctx.author.id]:
            user_business = await self.economy.get_user_business(ctx.author.id)
            if user_business:
                return await ctx.send_warning("You already own a business.")
            system_business = await self.economy.get_system_business(business)
            if not system_business:
                return await ctx.send_warning("This business doesn't exist.")
            user_economy = await self.bot.db.fetchrow("SELECT * FROM economy WHERE user_id = $1", ctx.author.id)
            if user_economy['cash'] < system_business["cost"]:
                return await ctx.send_warning("You don't have enough money to buy this business.")
            await self.bot.db.execute("INSERT INTO economy_business (user_id, last_collected, business_id) VALUES ($1, $2, $3)", ctx.author.id, datetime.datetime.now().timestamp(), system_business["business_id"])
            await self.bot.db.execute("UPDATE economy SET cash = cash - $1 WHERE user_id = $2", system_business["cost"], ctx.author.id)
            await self.economy.logging(ctx.author, Decimal(system_business["cost"]), "buy", "business")
            await self.economy.logging_business(ctx.author, self.bot.user, Decimal(system_business["cost"]), "buy", system_business["business_id"])
            return await ctx.send_success(f"You have successfully bought the business **{system_business['name']}** for **{self.bot.misc.humanize_number(system_business['cost'])}** {self.cash}")

    @business.command(name="sell", description="Sell your business")
    @create_account()
    async def business_sell(self, ctx: EvelinaContext):
        """Sell your business"""
        async with self.locks[ctx.author.id]:
            user_business = await self.economy.get_user_business(ctx.author.id)
            if not user_business:
                return await ctx.send_warning("You don't own any business.")
            system_business = await self.economy.get_system_business_by_id(user_business["business_id"])
            sale_price = system_business["cost"] // 2
        async def yes_callback(interaction: Interaction):
            user_business = await self.economy.get_user_business(ctx.author.id)
            if not user_business:
                return await interaction.response.edit_message(embed=Embed(description=f"{emojis.WARNING} {ctx.author.mention}: You don't own any business.", color=colors.WARNING), view=None)
            await self.bot.db.execute("DELETE FROM economy_business WHERE user_id = $1", ctx.author.id)
            await self.economy.logging(ctx.author, Decimal(sale_price), "sell", "business")
            await self.economy.logging_business(ctx.author, self.bot.user, Decimal(sale_price), "sell", user_business["business_id"])
            await self.bot.db.execute("UPDATE economy SET cash = cash + $1 WHERE user_id = $2", sale_price, ctx.author.id)
            check = await self.bot.db.fetchrow("SELECT * FROM economy_cards_used WHERE user_id = $1 AND business = $2", ctx.author.id, "business")
            if check:
                await self.bot.db.execute("UPDATE economy_cards_user SET active = True WHERE user_id = $1 AND card_id = $2", ctx.author.id, check['card_id'])
                await self.bot.db.execute("DELETE FROM economy_cards_used WHERE user_id = $1 AND card_id = $2", ctx.author.id, check['card_id'])
            await interaction.response.edit_message(embed=Embed(description=f"{emojis.APPROVE} {ctx.author.mention}: You have successfully sold the business **{system_business['name']}** for **{self.bot.misc.humanize_number(sale_price)}** {self.cash}", color=colors.SUCCESS), view=None)
        async def no_callback(interaction: Interaction):
            await interaction.response.edit_message(embed=Embed(description=f"{emojis.DENY} {ctx.author.mention}: Sale got canceled", color=colors.ERROR), view=None)
        return await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to sell **{system_business['name']}** for **{self.bot.misc.humanize_number(sale_price)}** {self.cash}?", yes_callback, no_callback)

    @business.command(name="info", aliases=["status"], usage="business info comminate", description="Get information about your business")
    @create_account()
    async def business_info(self, ctx: EvelinaContext, *, user: User = Author):
        """Get information about your business"""
        async with self.locks[ctx.author.id]:
            user_business = await self.economy.get_user_business(user.id)
            if not user_business:
                does = "don't" if user == ctx.author else f"doesn't"
                return await ctx.send_warning(f"{'You' if user == ctx.author else f'{user.mention}'} {does} own any business.")
            system_business = await self.economy.get_system_business_by_id(user_business["business_id"])
            if not system_business:
                return await ctx.send_warning("This business doesn't exist.")
            card_used = await self.bot.db.fetchrow("SELECT * FROM economy_cards_used WHERE user_id = $1 AND business = $2", user.id, "business")
            if card_used:
                card_user = await self.bot.db.fetchrow("SELECT * FROM economy_cards_user WHERE user_id = $1 AND card_id = $2", user.id, card_used["card_id"])
                if card_user:
                    card_info = await self.bot.db.fetchrow("SELECT * FROM economy_cards WHERE id = $1", card_user["id"])
                    if card_info:
                        hours = card_user["storage"]
                        multiplier = card_user["multiplier"]
                        image = card_info["image"]
                        name = card_info["name"]
            embed = Embed(title=f"{system_business['name']} {system_business['emoji']}", color=colors.NEUTRAL)
            embed.set_author(name=user.name, icon_url=user.avatar.url if user.avatar else user.default_avatar.url)
            if await self.economy.calculate_business_earning(ctx.author.id, user_business['last_collected'], system_business['earnings']) <= 0:
                next_collect = user_business['last_collected'] + 3600
                embed.description = f"Next collection time: <t:{next_collect}:R>"
            if card_used and card_user and card_info:
                stars = "⭐" * card_info["stars"]
                embed.set_thumbnail(url=image)
                embed.add_field(name="Manager", value=f"```{name} | {stars}```", inline=True)
                embed.add_field(name="Storage", value=f"```{hours}h```", inline=True)
                embed.add_field(name="Multiplier", value=f"```{multiplier}x```", inline=True)
            embed.add_field(name="State Value", value=f"```{self.bot.misc.humanize_clean_number(system_business['cost'])} {self.cash}```")
            if card_used and card_user and card_info:
                hour_revenue =  system_business['earnings'] * multiplier
                embed.add_field(name="Hour Revenue", value=f"```{self.bot.misc.humanize_clean_number(hour_revenue)} {self.cash}```")
            else:
                embed.add_field(name="Hour Revenue", value=f"```{self.bot.misc.humanize_clean_number(system_business['earnings'])} {self.cash}```")
            embed.add_field(name="Balance", value=f"```{self.bot.misc.humanize_clean_number(await self.economy.calculate_business_earning(ctx.author.id, user_business['last_collected'], system_business['earnings']))} {self.cash}```")
            return await ctx.send(embed=embed)

    @business.command(name="collect", description="Collect the balance from your business")
    @create_account()
    async def business_collect(self, ctx: EvelinaContext):
        """Collect the balance from your business"""
        old_business = await self.bot.db.fetchrow("SELECT * FROM business WHERE owner = $1", ctx.author.id)
        if old_business:
            return await ctx.send_warning(f"You have an old business, please migrate it using `{ctx.clean_prefix}business migrate`.")
        async with self.locks[ctx.author.id]:
            user_business = await self.economy.get_user_business(ctx.author.id)
            if not user_business:
                return await ctx.send_warning("You don't own any business.")
            system_business = await self.economy.get_system_business_by_id(user_business["business_id"])
            if not system_business:
                return await ctx.send_warning("This business doesn't exist.")
            if await self.economy.calculate_business_earning(ctx.author.id, user_business['last_collected'], system_business['earnings']) <= 0:
                next_collect = user_business['last_collected'] + 3600
                return await ctx.send_warning(f"You can **only** collect your lab earnings **once** every hour\n> Next collection time: <t:{next_collect}:R>")
            earnings = await self.economy.calculate_business_earning(ctx.author.id, user_business['last_collected'], system_business['earnings'])
            await self.bot.db.execute("UPDATE economy SET cash = cash + $1 WHERE user_id = $2", await self.economy.calculate_business_earning(ctx.author.id, user_business['last_collected'], system_business['earnings']), ctx.author.id)
            await self.bot.db.execute("UPDATE economy_business SET last_collected = $1 WHERE user_id = $2", datetime.datetime.now().timestamp(), ctx.author.id)
            await self.quests.add_collect_money(ctx.author, "business", Decimal(earnings))
            await self.economy.logging(ctx.author, Decimal(earnings), "collect", "business")
            await self.economy.logging_business(ctx.author, self.bot.user, Decimal(earnings), "collect", user_business["business_id"])
            return await ctx.send_success(f"You have successfully collected **{self.bot.misc.humanize_clean_number(earnings)}** {self.cash} from your business **{system_business['name']}**.")
    
    @business.command(name="list", description="List all businesses")
    @create_account()
    async def business_list(self, ctx: EvelinaContext):
        """List all businesses"""
        async with self.locks[ctx.author.id]:
            businesses = await self.economy.get_all_businesses()
            embeds = []
            for business in businesses:
                embed = Embed(title=f"{business['name']} {business['emoji']}", description=business['description'], color=colors.NEUTRAL)
                embed.add_field(name="Cost", value=f"{self.bot.misc.humanize_clean_number(business['cost'])} {self.cash}", inline=True)
                embed.add_field(name="Earnings per Hour", value=f"{self.bot.misc.humanize_clean_number(business['earnings'])} {self.cash}", inline=True)
                embed.set_image(url=business['image'])
                embed.set_footer(text=f"Page: {businesses.index(business) + 1}/{len(businesses)} ({len(businesses)} entries)")
                embeds.append(embed)
            return await ctx.paginator(embeds)
        
    @business.command(name="add", brief="bot helper", usage="business add comminate 1", description="Add a business to a user")
    @create_account()
    @is_moderator()
    async def business_add(self, ctx: EvelinaContext, user: User, business_id: int):
        """Add a business to a user"""
        business = await self.economy.get_system_business_by_id(business_id)
        if not business:
            return await ctx.send_warning("This business doesn't exist.")
        user_business = await self.economy.get_user_business(user.id)
        if user_business:
            return await ctx.send_warning(f"{user.mention} already owns a business.")
        await self.bot.db.execute("INSERT INTO economy_business (user_id, last_collected, business_id) VALUES ($1, $2, $3)", user.id, datetime.datetime.now().timestamp(), business_id)
        await self.bot.manage.logging(ctx.author, f"Added **{business['name']}** to {user.mention} (`{user.id}`)", "money")
        await self.economy.logging_business(user, ctx.author, Decimal(0), "add", business_id)
        return await ctx.send_success(f"Successfully added the business **{business['name']}** to {user.mention}.")

    @business.command(name="remove", brief="bot helper", usage="business remove comminate", description="Remove a business from a user")
    @create_account()
    @is_moderator()
    async def business_remove(self, ctx: EvelinaContext, user: User):
        """Remove a business from a user"""
        user_business = await self.economy.get_user_business(user.id)
        if not user_business:
            return await ctx.send_warning(f"{user.mention} doesn't own any business.")
        business = await self.economy.get_system_business_by_id(user_business["business_id"])
        if not business:
            return await ctx.send_warning("This business doesn't exist.")
        await self.bot.db.execute("DELETE FROM economy_business WHERE user_id = $1", user.id)
        await self.bot.manage.logging(ctx.author, f"Removed **{business['name']}** from {user.mention} (`{user.id}`)", "money")
        await self.economy.logging_business(user, ctx.author, Decimal(0), "remove", user_business["business_id"])
        return await ctx.send_success(f"Successfully removed the business from {user.mention}.")

    @group(name="lab", invoke_without_command=True, case_insensitive=True)
    async def lab(self, ctx: EvelinaContext):
        """Buy a laboratory business which generates money over time and needs to be maintained"""
        return await ctx.create_pages()

    @lab.command(name="buy")
    @create_account()
    async def lab_buy(self, ctx: EvelinaContext):
        """Buy a laboratory business"""
        check = await self.bot.db.fetchrow("SELECT cash FROM economy WHERE user_id = $1", ctx.author.id)
        lab = await self.bot.db.fetchrow("SELECT * FROM economy_lab WHERE user_id = $1", ctx.author.id)
        if lab:
            return await ctx.send_warning("You **already own** a laboratory.")
        lab_cost = 5000000
        if check and check["cash"] < lab_cost:
            return await ctx.send_warning(f"You **do not** have enough cash to buy a laboratory\n> You need **{self.bot.misc.humanize_number(lab_cost)}** {self.cash}")
        await self.bot.db.execute("UPDATE economy SET cash = cash - $1 WHERE user_id = $2", lab_cost, ctx.author.id)
        current_time = int(time.time())
        await self.bot.db.execute("INSERT INTO economy_lab (user_id, ampoules, last_collected, upgrade_state) VALUES ($1, 100, $2, 0)", ctx.author.id, current_time)
        await self.economy.logging(ctx.author, Decimal(lab_cost), "buy", "laboratory")
        await self.economy.logging_lab(ctx.author, self.bot.user, Decimal(lab_cost), "buy", 0)
        return await ctx.send_success("You've successfully **bought** a laboratory")
    
    @lab.command(name="ampoules", aliases=["restock", "ba"], usage="lab ampoules 20|all")
    @create_account()
    async def lab_ampoules(self, ctx: EvelinaContext, amount: str):
        """Buy ampoules for your laboratory"""
        check = await self.bot.db.fetchrow("SELECT cash FROM economy WHERE user_id = $1", ctx.author.id)
        lab = await self.bot.db.fetchrow("SELECT * FROM economy_lab WHERE user_id = $1", ctx.author.id)
        if not lab:
            return await ctx.send_warning("You **don't own** a laboratory.")
        current_ampoules = lab["ampoules"]
        upgrade_state = lab["upgrade_state"]
        earnings_per_hour, _, _ = await self.economy.calculate_lab_earnings_and_upgrade(ctx.author.id, upgrade_state)
        earnings_12_hours = earnings_per_hour * 12
        cost_for_100_ampoules = int(earnings_12_hours * 0.20)
        ampoule_cost = cost_for_100_ampoules / 100
        if amount.lower() == "all":
            max_affordable = min(
                int(check["cash"] / ampoule_cost),
                100 - current_ampoules
            )
            if max_affordable <= 0:
                return await ctx.send_warning("You either can't afford any ampoules or your laboratory is full")
            amount = max_affordable
        else:
            try:
                amount = int(amount)
            except ValueError:
                return await ctx.send_warning("Please provide a valid number or 'all'")
        if current_ampoules + amount > 100:
            return await ctx.send_warning("You can't have more than **100** ampoules in your laboratory")
        total_cost = int(ampoule_cost * amount)
        if check["cash"] < total_cost:
            return await ctx.send_warning(f"You **do not** have enough cash to buy **{amount}** ampoules\n> You need **{self.bot.misc.humanize_number(total_cost)}** {self.cash}")
        await self.bot.db.execute("UPDATE economy SET cash = cash - $1 WHERE user_id = $2", total_cost, ctx.author.id)
        await self.bot.db.execute("UPDATE economy_lab SET ampoules = ampoules + $1 WHERE user_id = $2", amount, ctx.author.id)
        await self.economy.logging(ctx.author, Decimal(total_cost), "buy", "ampoules")
        return await ctx.send_success(f"You've successfully bought **{amount}** ampoules for **{self.bot.misc.humanize_number(total_cost)}** {self.cash}")
        
    @lab.command(name="sell")
    @create_account()
    async def lab_sell(self, ctx: EvelinaContext):
        """Sell your laboratory business"""
        lab = await self.bot.db.fetchrow("SELECT * FROM economy_lab WHERE user_id = $1", ctx.author.id)
        if not lab:
            return await ctx.send_warning("You **don't own** a laboratory.")
        upgrade_state = lab["upgrade_state"]
        base_lab_cost = 5000000
        total_upgrade_cost = 0
        for level in range(1, upgrade_state + 1):
            _, _, upgrade_cost = await self.economy.calculate_lab_earnings_and_upgrade(ctx.author.id, level)
            total_upgrade_cost += upgrade_cost
        refund_amount = (base_lab_cost * 0.1) + (total_upgrade_cost * 0.1)
        async def yes_callback(interaction: Interaction):
            lab = await self.bot.db.fetchrow("SELECT * FROM economy_lab WHERE user_id = $1", ctx.author.id)
            if not lab:
                return await interaction.response.edit_message(embed=Embed(description=f"{emojis.WARNING} {ctx.author.mention}: You **do not** own a laboratory", color=colors.WARNING), view=None)
            await self.bot.db.execute("UPDATE economy SET cash = cash + $1 WHERE user_id = $2", refund_amount, ctx.author.id)
            await self.bot.db.execute("DELETE FROM economy_lab WHERE user_id = $1", ctx.author.id)
            await self.economy.logging(ctx.author, Decimal(refund_amount), "sell", "laboratory")
            await self.economy.logging_lab(ctx.author, self.bot.user, Decimal(refund_amount), "sell", upgrade_state)
            await interaction.response.edit_message(embed=Embed(description=f"{emojis.APPROVE} {ctx.author.mention}: You've **successfully** sold your laborator\n> Received: **{self.bot.misc.humanize_number(refund_amount)}** {self.cash}", color=colors.SUCCESS), view=None)
        async def no_callback(interaction: Interaction):
            await interaction.response.edit_message(embed=Embed(description=f"{emojis.DENY} {ctx.author.mention}: Sale got canceled", color=colors.ERROR), view=None)
        return await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to sell your lab for **{self.bot.misc.humanize_number(refund_amount)}** {self.cash}?", yes_callback, no_callback)

    @lab.command(name="upgrade", cooldown=5)
    @create_account()
    @cooldown(1, 5, BucketType.user)
    async def lab_upgrade(self, ctx: EvelinaContext):
        """Upgrade your laboratory business by one level."""
        check = await self.bot.db.fetchrow("SELECT cash FROM economy WHERE user_id = $1", ctx.author.id)
        lab = await self.bot.db.fetchrow("SELECT * FROM economy_lab WHERE user_id = $1", ctx.author.id)
        if not lab:
            return await ctx.send_warning("You **don't own** a laboratory.")

        upgrade_state = lab["upgrade_state"]
        if upgrade_state >= 50:
            return await ctx.send_warning("You've **maxed out** your lab")

        _, _, next_upgrade_cost = await self.economy.calculate_lab_earnings_and_upgrade(ctx.author.id, upgrade_state)
        if check["cash"] < next_upgrade_cost:
            return await ctx.send_warning(
                f"You **do not** have enough cash to upgrade\nYou need **{self.bot.misc.humanize_number(next_upgrade_cost)}** {self.cash}"
            )

        await self.bot.db.execute(
            "UPDATE economy SET cash = cash - $1 WHERE user_id = $2", next_upgrade_cost, ctx.author.id
        )
        await self.bot.db.execute(
            "UPDATE economy_lab SET upgrade_state = upgrade_state + 1 WHERE user_id = $1", ctx.author.id
        )

        await self.economy.logging(ctx.author, Decimal(next_upgrade_cost), "upgrade", "laboratory")
        await self.economy.logging_lab(ctx.author, self.bot.user, Decimal(next_upgrade_cost), "upgrade", upgrade_state)

        return await ctx.send_success(
            f"You've successfully upgraded your lab to level **{upgrade_state + 1}**\n"
            f"> The total upgrade cost was **{self.bot.misc.humanize_number(next_upgrade_cost)}** {self.cash}"
        )

    @lab.command(name="info", aliases=["status"], usage="lab status comminate")
    @create_account()
    async def lab_info(self, ctx: EvelinaContext, user: User = Author):
        """Check the status of your laboratory business"""
        lab = await self.bot.db.fetchrow("SELECT * FROM economy_lab WHERE user_id = $1", user.id)
        if not lab:
            return await ctx.send_warning("You **don't own** a laboratory.")
        current_time = int(time.time())
        last_collected = lab["last_collected"]
        upgrade_state = lab["upgrade_state"]
        earnings_per_hour, earnings_cap, next_upgrade_cost = await self.economy.calculate_lab_earnings_and_upgrade(user.id, upgrade_state)
        time_passed = current_time - last_collected
        card_used = await self.bot.db.fetchrow("SELECT * FROM economy_cards_used WHERE user_id = $1 AND business = $2", user.id, "lab")
        if card_used:
            card_user = await self.bot.db.fetchrow("SELECT * FROM economy_cards_user WHERE user_id = $1 AND card_id = $2", user.id, card_used["card_id"])
            if card_user:
                card_info = await self.bot.db.fetchrow("SELECT * FROM economy_cards WHERE id = $1", card_user["id"])
                if card_info:
                    hours = card_user["storage"]
                    multiplier = card_user["multiplier"]
                    image = card_info["image"]
                    name = card_info["name"]
        if time_passed < 3600:
            embed = Embed(title="Laboratory Status", color=colors.ECONOMY)
            next_collect_time = last_collected + 3600
            embed.description = f"Next collection time: <t:{next_collect_time}:R>"
            if card_used and card_user and card_info:
                stars = "⭐" * card_info["stars"]
                embed.set_thumbnail(url=image)
                embed.add_field(name="Manager", value=f"```{name} | {stars}```", inline=True)
                embed.add_field(name="Storage", value=f"```{hours}h```", inline=True)
                embed.add_field(name="Multiplier", value=f"```{multiplier}x```", inline=True)
            embed.add_field(name="Ampoules", value=f"```{lab['ampoules']}```", inline=True)
            embed.add_field(name="Upgrade State", value=f"```{upgrade_state}```", inline=True)
            embed.add_field(name="Earnings per Hour", value=f"```{self.bot.misc.humanize_number(earnings_per_hour)} {self.cash}```", inline=True)
            if upgrade_state >= 50:
                embed.add_field(name="Next Upgrade Cost", value="```Maxed Out```", inline=True)
            else:
                embed.add_field(name="Next Upgrade Cost", value=f"```{self.bot.misc.humanize_number(next_upgrade_cost)}```", inline=True)
            return await ctx.send(embed=embed)
        hours_passed = time_passed // 3600
        earnings = earnings_per_hour * hours_passed
        if earnings > earnings_cap:
            earnings = earnings_cap
        embed = Embed(title="Laboratory Status", color=colors.ECONOMY)
        if card_used and card_user and card_info:
            stars = "⭐" * card_info["stars"]
            embed.set_thumbnail(url=image)
            embed.add_field(name="Scientist", value=f"```{name} | {stars}```", inline=True)
            embed.add_field(name="Storage", value=f"```{hours}h```", inline=True)
            embed.add_field(name="Multiplier", value=f"```{multiplier}x```", inline=True)
        embed.add_field(name="Ampoules", value=f"```{lab['ampoules']}```", inline=True)
        embed.add_field(name="Upgrade State", value=f"```{upgrade_state}```", inline=True)
        embed.add_field(name="Earnings per Hour", value=f"```{self.bot.misc.humanize_number(earnings_per_hour)} {self.cash}```", inline=True)
        if upgrade_state >= 50:
            embed.add_field(name="Next Upgrade Cost", value="```Maxed Out```", inline=True)
        else:
            embed.add_field(name="Next Upgrade Cost", value=f"```{self.bot.misc.humanize_number(next_upgrade_cost)}```", inline=True)
        embed.add_field(name="Earnings", value=f"```{self.bot.misc.humanize_number(earnings)} {self.cash}```", inline=True)
        if earnings == earnings_cap:
            embed.add_field(name=f"{emojis.WARNING} Storage", value=f"```{self.bot.misc.humanize_number(earnings_cap)} {self.cash}```", inline=True)
        else:
            embed.add_field(name="Storage", value=f"```{self.bot.misc.humanize_number(earnings_cap)} {self.cash}```", inline=True)
        return await ctx.send(embed=embed)
    
    @lab.command(name="collect")
    @create_account()
    async def lab_collect(self, ctx: EvelinaContext):
        """Collect your laboratory business earnings"""
        lab = await self.bot.db.fetchrow("SELECT * FROM economy_lab WHERE user_id = $1", ctx.author.id)
        if not lab:
            return await ctx.send_warning("You **don't own** a laboratory.")
        
        current_time = int(time.time())
        last_collected = lab["last_collected"]
        upgrade_state = lab["upgrade_state"]
        ampoules = lab["ampoules"]
        time_passed = current_time - last_collected

        if time_passed < 3600:
            next_collect_time = last_collected + 3600
            next_collect_time_str = f"<t:{next_collect_time}:R>"
            return await ctx.send_warning(f"You can **only** collect your lab earnings **once** every hour\nNext collection time: {next_collect_time_str}")

        _, _, storage, _ = await self.economy.get_used_card(ctx.author.id, "lab")
        if storage is None:
            storage = 6

        hours_passed = min(time_passed // 3600, int(storage))
        ampoules_needed = hours_passed * 5

        if ampoules < ampoules_needed:
            return await ctx.send_warning("You **do not** have enough ampoules to collect your earnings.")

        earnings_per_hour, earnings_cap, _ = await self.economy.calculate_lab_earnings_and_upgrade(ctx.author.id, upgrade_state)
        earnings = earnings_per_hour * hours_passed
        if earnings > earnings_cap:
            earnings = earnings_cap

        await self.bot.db.execute("UPDATE economy SET cash = cash + $1 WHERE user_id = $2", earnings, ctx.author.id)
        await self.bot.db.execute("UPDATE economy_lab SET last_collected = $1, ampoules = ampoules - $2 WHERE user_id = $3", current_time, ampoules_needed, ctx.author.id)
        
        next_collect_time = current_time + 3600
        next_collect_time_str = f"<t:{next_collect_time}:R>"

        await self.quests.add_collect_money(ctx.author, "lab", Decimal(earnings))
        await self.economy.logging(ctx.author, Decimal(earnings), "collect", "laboratory")
        await self.economy.logging_lab(ctx.author, self.bot.user, Decimal(earnings), "collect", upgrade_state)

        return await ctx.send_success(f"You've collected **${self.bot.misc.humanize_number(earnings)}** {self.cash}\nNext collection available {next_collect_time_str}")

    @lab.command(name="add", brief="bot moderator", usage="lab add comminate 1", description="Add a laboratory to a user")
    @create_account()
    @is_moderator()
    async def lab_add(self, ctx: EvelinaContext, user: User, upgrade_state: int):
        """Add a laboratory to a user"""
        lab = await self.bot.db.fetchrow("SELECT * FROM economy_lab WHERE user_id = $1", user.id)
        if lab:
            return await ctx.send_warning(f"{user.mention} already owns a laboratory.")
        await self.bot.db.execute("INSERT INTO economy_lab (user_id, ampoules, last_collected, upgrade_state) VALUES ($1, 100, $2, $3)", user.id, int(time.time()), upgrade_state)
        await self.bot.manage.logging(ctx.author, f"Added a laboratory to {user.mention} (`{user.id}`)", "money")
        await self.economy.logging_lab(user, ctx.author, Decimal(0), "add", upgrade_state)
        return await ctx.send_success(f"Successfully added a laboratory to {user.mention}.")
    
    @lab.command(name="remove", brief="bot moderator", usage="lab remove comminate", description="Remove a laboratory from a user")
    @create_account()
    @is_moderator()
    async def lab_remove(self, ctx: EvelinaContext, user: User):
        """Remove a laboratory from a user"""
        lab = await self.bot.db.fetchrow("SELECT * FROM economy_lab WHERE user_id = $1", user.id)
        if not lab:
            return await ctx.send_warning(f"{user.mention} doesn't own a laboratory.")
        await self.bot.db.execute("DELETE FROM economy_lab WHERE user_id = $1", user.id)
        await self.bot.manage.logging(ctx.author, f"Removed a laboratory from {user.mention} (`{user.id}`)", "money")
        await self.economy.logging_lab(user, ctx.author, Decimal(0), "remove", lab["upgrade_state"])
        return await ctx.send_success(f"Successfully removed the laboratory from {user.mention}.")

    @group(name="shop", invoke_without_command=True, case_insensitive=True)
    async def shop(self, ctx: EvelinaContext):
        """Manage you server economy shop"""
        return await ctx.create_pages()
    
    @shop.command(name="enable", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def shop_enable(self, ctx: EvelinaContext):
        """Enable your server economy shop"""
        check = await self.bot.db.fetchrow("SELECT * FROM economy_shop WHERE guild_id = $1", ctx.guild.id)
        if check and check['state'] == True:
            return await ctx.send_warning("Your economy shop is **already** enabled")
        elif check and check['state'] == False:
            await self.bot.db.execute("UPDATE economy_shop SET state = True WHERE guild_id = $1", ctx.guild.id)
            return await ctx.send_success("Changed your economy shop to **enabled**")
        elif not check:
            await self.bot.db.execute("INSERT INTO economy_shop VALUES ($1, $2)", ctx.guild.id, True)
            return await ctx.send_success("Your economy shop got **enabled**")
        
    @shop.command(name="disable", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def shop_disable(self, ctx: EvelinaContext):
        """Disable your server economy shop"""
        check = await self.bot.db.fetchrow("SELECT * FROM economy_shop WHERE guild_id = $1", ctx.guild.id)
        if check and check['state'] == False:
            return await ctx.send_warning("Your economy shop is **already** disabled")
        elif check and check['state'] == True:
            await self.bot.db.execute("UPDATE economy_shop SET state = False WHERE guild_id = $1", ctx.guild.id)
            return await ctx.send_success("Changed your economy shop to **disabled**")
        elif not check:
            await self.bot.db.execute("INSERT INTO economy_shop VALUES ($1, $2)", ctx.guild.id, False)
            return await ctx.send_success("Your economy shop got **disabled**")
        
    @shop.command(name="add", brief="manage guild", usage="shop add @gambler 20.000 Gamble King --limit 5", extras={"limit": "Set a purchase limit", "time": "Set a time limit"})
    @has_guild_permissions(manage_guild=True)
    async def shop_add(self, ctx: EvelinaContext, role: NewRoleConverter, amount: Amount, *, name: str):
        """Add a item to your economy shop"""
        flags = {
            "--limit": None,
            "--time": None
        }
        for flag in flags.keys():
            match = re.search(rf"{re.escape(flag)}\s+(\S+)", name)
            if match:
                flags[flag] = match.group(1)
                name = re.sub(rf"{re.escape(flag)}\s+\S+", "", name).strip()
        limit = None
        time = None
        total_time = None
        if flags["--limit"]:
            try:
                limit = int(flags["--limit"])
            except ValueError:
                return await ctx.send_warning("Invalid limit value provided.")
        if flags["--time"]:
            try:
                time = await ValidTime().convert(ctx, flags["--time"])
                total_time = datetime.datetime.now().timestamp() + time
            except Exception:
                return await ctx.send_warning("Invalid time value provided.")
        check = await self.bot.db.fetchrow("SELECT * FROM economy_shop_items WHERE guild_id = $1 AND role_id = $2", ctx.guild.id, role.id)
        if check:
            return await ctx.send_warning(f"Item {role.mention} already exist as **{check['name']}** for **{self.bot.misc.humanize_clean_number(check['amount'])}** {self.cash}")
        else:
            await self.bot.db.execute("INSERT INTO economy_shop_items VALUES ($1, $2, $3, $4, $5, $6)", ctx.guild.id, role.id, amount, name, limit, total_time)
            return await ctx.send_success(f"Item {role.mention} added as **{name}** for **{self.bot.misc.humanize_clean_number(amount)}** {self.cash}")
        
    @shop.command(name="remove", brief="manage guild", usage="shop remove @gambler")
    @has_guild_permissions(manage_guild=True)
    async def shop_remove(self, ctx: EvelinaContext, role: NewRoleConverter):
        """Remove a item from your economy shop"""
        check = await self.bot.db.fetchrow("SELECT * FROM economy_shop_items WHERE guild_id = $1 AND role_id = $2", ctx.guild.id, role.id)
        if not check:
            return await ctx.send_warning(f"Item {role.mention} doesn't exist")
        else:
            await self.bot.db.execute("DELETE FROM economy_shop_items WHERE guild_id = $1 AND role_id = $2", ctx.guild.id, role.id)
            return await ctx.send_success(f"Item {role.mention} got removed from economy shop")
        
    @shop.command(name="view")
    async def shop_view(self, ctx: EvelinaContext):
        """Displays all items in the economy shop"""
        check = await self.bot.db.fetchrow("SELECT * FROM economy_shop WHERE guild_id = $1", ctx.guild.id)
        if check and check['state'] == False:
            return await ctx.send_warning("Economy shop is **disabled**")
        items = await self.bot.db.fetch("SELECT * FROM economy_shop_items WHERE guild_id = $1", ctx.guild.id)
        if not items:
            return await ctx.send_warning("There are no items available in the shop.")
        user_roles = {role.id for role in ctx.author.roles}
        embeds = []
        entries_per_page = 6
        total_pages = (len(items) + entries_per_page - 1) // entries_per_page
        for i in range(0, len(items), entries_per_page):
            page_number = (i // entries_per_page) + 1
            embed = Embed(title="Economy Shop", color=colors.NEUTRAL)
            for item in items[i:i + entries_per_page]:
                role = ctx.guild.get_role(item['role_id'])
                if role:
                    item_name = item['name']
                    item_price = self.bot.misc.humanize_clean_number(item['amount'])
                    item_limit = item['limit'] if item['limit'] is not None else "Unlimited"
                    item_time = f"<t:{item['time']}:R>" if item['time'] is not None else "Never"
                    user_has_item = emojis.APPROVE if role.id in user_roles else emojis.DENY
                    embed.add_field(
                        name=f"> {item_name}",
                        value=f"**Role:** {role.mention}\n**Price:** {item_price} {self.cash}\n**Stock:** {item_limit}\n**Expires:** {item_time}\n**Purchased:** {user_has_item}",
                        inline=True
                    )
            embed.set_footer(text=f"Page: {page_number}/{total_pages} ({len(items)} entries)")
            embeds.append(embed)
        await ctx.paginator(embeds)

    @shop.command(name="buy")
    @create_account()
    @bot_has_guild_permissions(manage_roles=True)
    async def shop_buy(self, ctx: EvelinaContext, *, name: str):
        """Buy an item from the economy shop"""
        check = await self.bot.db.fetchrow("SELECT * FROM economy_shop WHERE guild_id = $1", ctx.guild.id)
        if check and check['state'] == False:
            return await ctx.send_warning("Economy shop is **disabled**")
        item = await self.bot.db.fetchrow("SELECT * FROM economy_shop_items WHERE guild_id = $1 AND name = $2", ctx.guild.id, name)
        if not item:
            return await ctx.send_warning(f"**{name}** is not available in the shop")
        user_balance = await self.bot.db.fetchval("SELECT cash FROM economy WHERE user_id = $1", ctx.author.id)
        if user_balance is None or user_balance < item["amount"]:
            return await ctx.send_warning("You don't have enough money to buy this item")
        role = ctx.guild.get_role(item['role_id'])
        if role.id in {r.id for r in ctx.author.roles}:
            return await ctx.send_warning("You already have this role and can't buy it again.")
        if item['time'] is not None and item['time'] < datetime.datetime.utcnow().timestamp():
            return await ctx.send_warning(f"Item **{name}** has expired <t:{item['time']}:R>")
        if item['limit'] is not None:
            if item['limit'] < 1:
                return await ctx.send_warning(f"Item **{name}** is out of stock")
            await self.bot.db.execute('UPDATE economy_shop_items SET "limit" = "limit" - 1 WHERE guild_id = $1 AND name = $2', ctx.guild.id, name)
        await self.bot.db.execute("UPDATE economy SET cash = cash - $1 WHERE user_id = $2", item["amount"], ctx.author.id)
        await self.bot.db.execute("INSERT INTO economy_shop_earnings (guild_id, amount) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET amount = economy_shop_earnings.amount + $2", ctx.guild.id, (item["amount"] * 0.75))
        await ctx.author.add_roles(role, reason=f"[Economy] Purchased for {item['amount']}")
        await self.economy.logging(ctx.author, Decimal(item["amount"]), "buy", "shop")
        return await ctx.send_success(f"You have successfully purchased {role.mention} for **{self.bot.misc.humanize_clean_number(item['amount'])} {self.cash}**")

    @shop.command(name="collect")
    @create_account()
    @has_guild_permissions(administrator=True)
    async def shop_collect(self, ctx: EvelinaContext):
        """Collect the earnings from the economy shop"""
        check = await self.bot.db.fetchrow("SELECT * FROM economy_shop WHERE guild_id = $1", ctx.guild.id)
        if not check or check['state'] == False:
            return await ctx.send_warning("Economy shop is **disabled**")
        earnings = await self.bot.db.fetchval("SELECT amount FROM economy_shop_earnings WHERE guild_id = $1", ctx.guild.id)
        if earnings is None or earnings == 0:
            return await ctx.send_warning("There are no earnings to collect")
        await self.bot.db.execute("UPDATE economy_shop_earnings SET amount = 0 WHERE guild_id = $1", ctx.guild.id)
        await self.bot.db.execute("UPDATE economy SET cash = cash + $1 WHERE user_id = $2", earnings, ctx.author.id)
        await self.economy.logging(ctx.author, Decimal(earnings), "collect", "shop")
        return await ctx.send_success(f"You have successfully collected **{self.bot.misc.humanize_clean_number(earnings)} {self.cash}**")

    @shop.command(name="balance")
    @create_account()
    @has_guild_permissions(administrator=True)
    async def shop_balance(self, ctx: EvelinaContext):
        """Check the current balance of the economy shop"""
        check = await self.bot.db.fetchrow("SELECT * FROM economy_shop WHERE guild_id = $1", ctx.guild.id)
        if not check or check['state'] == False:
            return await ctx.send_warning("Economy shop is **disabled**")
        earnings = await self.bot.db.fetchval("SELECT amount FROM economy_shop_earnings WHERE guild_id = $1", ctx.guild.id)
        earnings = earnings if earnings is not None else 0
        return await ctx.economy_send(f"Current balance of the economy shop is **{self.bot.misc.humanize_clean_number(earnings)} {self.cash}**")

    @group(name="company", aliases=["comp"], invoke_without_command=True, case_insensitive=True)
    @create_account()
    async def company(self, ctx: EvelinaContext):
        """Manage your company"""
        return await ctx.create_pages()
    
    @command(name="networth", aliases=["nw"], usage="networth comminate")
    @create_account()
    async def networth(self, ctx: EvelinaContext, user: User = None):
        """Check your networth"""
        user = user or ctx.author
        networth = await self.economy.get_user_networth(user.id)
        return await ctx.evelina_send(f"{user.mention} has a networth of **{self.bot.misc.humanize_number(networth)}** {self.cash}")

    @company.command(name="create", usage="company create ADCD addicted")
    @create_account()
    async def company_create(self, ctx: EvelinaContext, tag: ValidCompanyTag, *, name: ValidCompanyName):
        """Create a company"""
        user_company = await self.economy.get_user_company(ctx.author.id)
        if user_company:
            return await ctx.send_warning("You are already in a company.")
        limit = await self.economy.get_level_info(1)
        check = await self.bot.db.fetchrow("SELECT * FROM economy WHERE user_id = $1", ctx.author.id)
        if check["cash"] < limit["cost"]:
            return await ctx.send_warning(f"You do not have enough cash to create a company\n> You need **{self.bot.misc.humanize_clean_number(limit['cost'])}** {self.cash}")
        await self.bot.db.execute("UPDATE economy SET cash = cash - $1 WHERE user_id = $2", limit["cost"], ctx.author.id)
        await self.bot.db.execute(
            "INSERT INTO company (name, ceo, members, privacy, roles, level, vault, reputation, votes, tag, created, description, icon) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)",
            name, ctx.author.id, [ctx.author.id], 'public', '{}', 1, 0, 0, 0, str(tag).upper(), datetime.datetime.now().timestamp(), None, None
        )
        await self.economy.logging(ctx.author, Decimal(limit["cost"]), "create", "company")
        return await ctx.send_success(f"Successfully created the company [`{str(tag).upper()}`] **{name}**")

    @company.command(name="delete")
    @create_account()
    async def company_delete(self, ctx: EvelinaContext):
        """Delete your company permanently"""
        company = await self.economy.get_user_company(ctx.author.id)
        if not company:
            return await ctx.send_warning("You are not in a company.")
        if await self.economy.get_user_rank(ctx.author.id) < 4:
            return await ctx.send_warning("You are **missing** the following permission: `CEO`")
        async def yes_callback(interaction: Interaction):
            await self.economy.clear_company(company)
            return await interaction.response.edit_message(embed=Embed(description=f"{emojis.APPROVE} {ctx.author.mention}: Company **{company['name']}** has been permanently deleted.", color=colors.SUCCESS), view=None)
        async def no_callback(interaction: Interaction):
            return await interaction.response.edit_message(embed=Embed(description=f"{emojis.DENY} {ctx.author.mention}: Company deletion was canceled.", color=colors.ERROR), view=None)
        return await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to permanently delete the company **{company['name']}**?", yes_callback, no_callback)

    @company.command(name="transfer", usage="company transfer comminate")
    @create_account()
    async def company_transfer(self, ctx: EvelinaContext, user: Member):
        """Transfer the ownership of the company to another member"""
        company = await self.economy.get_user_company(ctx.author.id)
        if not company:
            return await ctx.send_warning("You are not in a company.")
        if await self.economy.get_user_rank(ctx.author.id) < 4:
            return await ctx.send_warning("You are **missing** the following permission: `CEO`")
        if user.id not in company["members"]:
            return await ctx.send_warning(f"{user.mention} is not in your company.")
        if user.id == ctx.author.id:
            return await ctx.send_warning("You can't transfer ownership to yourself.")
        limit = await self.economy.get_level_info(company['level'])
        roles = company.get('roles', {})
        if isinstance(roles, str):
            roles = json.loads(roles)
        if len(roles.get('Manager', [])) >= limit['managers']:
            return await ctx.send_warning(f"Your company is already at the maximum Manager limit of **{limit['managers']}**")
        async def yes_callback(interaction: Interaction):
            roles.setdefault('Manager', []).append(ctx.author.id)
            if await self.economy.get_user_rank(user.id) == 3:
                roles['Manager'].remove(user.id)
            if await self.economy.get_user_rank(user.id) == 2:
                roles['Senior'].remove(user.id)
            await self.bot.db.execute("UPDATE company SET ceo = $1, roles = $2 WHERE id = $3", user.id, json.dumps(roles), company['id'])
            return await interaction.response.edit_message(embed=Embed(description=f"{emojis.APPROVE} {ctx.author.mention}: {user.mention} is now the CEO of the company. You have been demoted to Manager.", color=colors.SUCCESS), view=None)
        async def no_callback(interaction: Interaction):
            return await interaction.response.edit_message(embed=Embed(description=f"{emojis.DENY} {ctx.author.mention}: Ownership transfer was canceled.", color=colors.ERROR), view=None)
        return await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to transfer ownership of the company to {user.mention}?", yes_callback, no_callback)

    @company.command(name="info", usage="company info monkeys")
    @create_account()
    async def company_info(self, ctx: EvelinaContext, *, name: str = None):
        """Show information about your company or another company"""
        if name:
            company = await self.economy.get_company(name)
            if not company:
                company = await self.economy.get_tag_company(name)
                if not company:
                    return await ctx.send_warning("Company with this name does not exist.")
        else:
            company = await self.economy.get_user_company(ctx.author.id)
            if not company:
                return await ctx.send_warning("You are not in a company.")
        roles = company.get('roles', {})
        if isinstance(roles, str):
            roles = json.loads(roles)
        limit = await self.economy.get_level_info(company['level'])
        company_name = company['name']
        company_tag = company['tag']
        company_icon = company['icon'] if company['icon'] else None
        company_description = company['description'] if company['description'] else ""
        company_ceo = self.bot.get_user(company['ceo']) or await self.bot.fetch_user(company['ceo'])
        company_member = len(company['members'])
        company_member_limit = limit['members']
        company_created = f"<t:{company['created']}:f>"
        company_list = await self.bot.db.fetch("SELECT name, reputation FROM company ORDER BY reputation DESC")
        company_rank = next((index for index, c in enumerate(list(company_list), start=1) if c['name'] == company_name), None)
        company_reputation = company['reputation']
        company_level = company['level']
        company_vault = self.bot.misc.humanize_number(company['vault'])
        company_networth = sum(await asyncio.gather(*(self.economy.get_user_networth(member_id) for member_id in company['members'])))
        company_votes_total = await self.bot.db.fetchval("SELECT COALESCE(SUM(votes), 0) FROM company_voters WHERE company_id = $1", company['id'])
        company_votes = company['votes']
        company_project = await self.bot.db.fetchrow("SELECT * FROM company_projects_started WHERE company_id = $1 AND active = $2", company['id'], True)
        if company_project:
            project = await self.bot.db.fetchrow("SELECT * FROM company_projects WHERE name = $1", company_project['project_name'])
            total_money = self.bot.misc.humanize_number(company_project['money'])
            needed_money = self.bot.misc.humanize_number(project['cost'])
            total_votes = self.bot.misc.humanize_clean_number(company['votes'])
            needed_votes = self.bot.misc.humanize_clean_number(project['votes'])
        embed = Embed(title=f"{company_name} | {company_tag}", description=company_description, color=colors.NEUTRAL)
        embed.add_field(name="👑 CEO", value=company_ceo.mention, inline=True)
        embed.add_field(name="👤 Members", value=f"{company_member}/{company_member_limit}", inline=True)
        embed.add_field(name="📅 Since", value=company_created, inline=True)
        embed.add_field(name="🏅 Rank", value=f"#{company_rank}", inline=True)
        embed.add_field(name="⭐ Reputation", value=company_reputation, inline=True)
        embed.add_field(name="🏢 Stage", value=company_level, inline=True)
        embed.add_field(name="💰 Vault", value=f"{company_vault} {self.cash}", inline=True)
        embed.add_field(name="📈 Networth", value=f"{self.bot.misc.humanize_number(company_networth)} {self.cash}", inline=True)
        embed.add_field(name="⬆️ Votes / Total Votes", value=f"{company_votes} / {company_votes_total}", inline=True)
        if company_project:
            embed.add_field(name=f"🚀 Project ({company_project['project_name']})", value=f"**Money:** {total_money}/{needed_money} {self.cash}\n**Votes:** {total_votes}/{needed_votes}", inline=False)
        embed.set_thumbnail(url=company_icon)
        view = CompanyInfoView(ctx, company, self.bot)
        return await ctx.send(embed=embed, view=view)
    
    @company.command(name="userinfo", aliases=["ui", "user"], usage="company userinfo comminate")
    @create_account()
    async def company_userinfo(self, ctx: EvelinaContext, user: User = Author):
        """Show information about a user in your company"""
        company = await self.economy.get_user_company(user.id)
        if not company:
            return await ctx.send_warning(f"{user.mention} is not in a company.")
        roles = company.get('roles', {})
        if isinstance(roles, str):
            roles = json.loads(roles)
        limit = await self.economy.get_level_info(company['level'])
        company_name = company['name']
        company_tag = company['tag']
        company_icon = company['icon'] if company['icon'] else None
        company_description = company['description'] if company['description'] else ""
        company_ceo = self.bot.get_user(company['ceo']) or await self.bot.fetch_user(company['ceo'])
        company_member = len(company['members'])
        company_member_limit = limit['members']
        company_created = f"<t:{company['created']}:f>"
        company_list = await self.bot.db.fetch("SELECT name, reputation FROM company ORDER BY reputation DESC")
        company_rank = next((index for index, c in enumerate(list(company_list), start=1) if c['name'] == company_name), None)
        company_reputation = company['reputation']
        company_level = company['level']
        company_vault = self.bot.misc.humanize_number(company['vault'])
        company_networth = sum(await asyncio.gather(*(self.economy.get_user_networth(member_id) for member_id in company['members'])))
        company_votes_total = await self.bot.db.fetchval("SELECT COALESCE(SUM(votes), 0) FROM company_voters WHERE company_id = $1", company['id'])
        company_votes = company['votes']
        company_project = await self.bot.db.fetchrow("SELECT * FROM company_projects_started WHERE company_id = $1 AND active = $2", company['id'], True)
        if company_project:
            project = await self.bot.db.fetchrow("SELECT * FROM company_projects WHERE name = $1", company_project['project_name'])
            total_money = self.bot.misc.humanize_number(company_project['money'])
            needed_money = self.bot.misc.humanize_number(project['cost'])
            total_votes = self.bot.misc.humanize_clean_number(company['votes'])
            needed_votes = self.bot.misc.humanize_clean_number(project['votes'])
        embed = Embed(title=f"{company_name} | {company_tag}", description=company_description, color=colors.NEUTRAL)
        embed.add_field(name="👑 CEO", value=company_ceo.mention, inline=True)
        embed.add_field(name="👤 Members", value=f"{company_member}/{company_member_limit}", inline=True)
        embed.add_field(name="📅 Since", value=company_created, inline=True)
        embed.add_field(name="🏅 Rank", value=f"#{company_rank}", inline=True)
        embed.add_field(name="⭐ Reputation", value=company_reputation, inline=True)
        embed.add_field(name="🏢 Stage", value=company_level, inline=True)
        embed.add_field(name="💰 Vault", value=f"{company_vault} {self.cash}", inline=True)
        embed.add_field(name="📈 Networth", value=f"{self.bot.misc.humanize_number(company_networth)} {self.cash}", inline=True)
        embed.add_field(name="⬆️ Votes / Total Votes", value=f"{company_votes} / {company_votes_total}", inline=True)
        if company_project:
            embed.add_field(name=f"🚀 Project ({company_project['project_name']})", value=f"**Money:** {total_money}/{needed_money} {self.cash}\n**Votes:** {total_votes}/{needed_votes}", inline=False)
        embed.set_thumbnail(url=company_icon)
        view = CompanyInfoView(ctx, company, self.bot)
        return await ctx.send(embed=embed, view=view)
    
    @company.command(name="list")
    @create_account()
    async def company_list(self, ctx: EvelinaContext):
        """List all companys"""
        results = await self.bot.db.fetch("SELECT * FROM company ORDER BY array_length(members, 1) DESC")
        if not results:
            return await ctx.send_warning(f"No **companys** found in the database.")
        company_entries = []
        for result in results:
            limit = await self.economy.get_level_info(result['level'])
            name = result['name']
            tag = result['tag']
            ceo = result['ceo']
            members = len(result['members'])
            members_limit = limit['members']
            networth = sum(await asyncio.gather(*(self.economy.get_user_networth(member_id) for member_id in result['members'])))
            entry = {"name": name, "tag": tag, "ceo": ceo, "members": f"{members}/{members_limit}", "networth": networth}
            company_entries.append(entry)
        embeds = []
        entries_per_page = 6
        total_pages = (len(company_entries) + entries_per_page - 1) // entries_per_page
        for i in range(0, len(company_entries), entries_per_page):
            page_number = (i // entries_per_page) + 1
            embed = Embed(title=f"Companies", color=colors.NEUTRAL)
            for entry in company_entries[i:i + entries_per_page]:
                embed.add_field(
                    name=f"{entry['name']} | {entry['tag']}",
                    value=f"**CEO:** <@{entry['ceo']}>\n"
                          f"**Members:** {entry['members']}\n"
                          f"**Networth:** {self.bot.misc.humanize_number(entry['networth'])} {self.cash}",
                    inline=True
                )
            embed.set_footer(text=f"Page: {page_number}/{total_pages} ({len(company_entries)} entries)")
            embeds.append(embed)
        await ctx.paginator(embeds)

    @company.group(name="members", invoke_without_command=True, case_insensitive=True)
    @create_account()
    async def company_members(self, ctx: EvelinaContext):
        """Manage your company members"""
        return await ctx.create_pages()

    @company_members.command(name="stats")
    @create_account()
    async def company_members_stats(self, ctx: EvelinaContext):
        """List all members of your company with their stats"""
        company = await self.economy.get_user_company(ctx.author.id)
        if not company:
            return await ctx.send_warning("You are not in a company.")
        roles = company.get('roles', {})
        if isinstance(roles, str):
            roles = json.loads(roles)
        ranks = {
            company['ceo']: "CEO",
            **{user_id: "Manager" for user_id in roles.get('Manager', [])},
            **{user_id: "Senior" for user_id in roles.get('Senior', [])},
        }
        rank_priority = {"CEO": 1, "Manager": 2, "Senior": 3, "Employee": 4}
        sorted_members = sorted(company['members'], key=lambda x: rank_priority.get(ranks.get(x, "Employee")))
        members_stats = []
        for member_id in sorted_members:
            user = self.bot.get_user(member_id) or await self.bot.fetch_user(member_id)
            rank = ranks.get(member_id, "Employee")
            networth = await self.economy.get_user_networth(member_id)
            votes = company['votes']
            members_stats.append((user.name, f"**Rank:** {rank}\n**Votes:** {votes}\n**Networth:** {self.bot.misc.humanize_number(networth)} {self.cash}"))
        embeds = []
        entries_per_page = 9
        total_pages = (len(members_stats) + entries_per_page - 1) // entries_per_page
        for i in range(0, len(members_stats), entries_per_page):
            page_number = (i // entries_per_page) + 1
            embed = Embed(title=f"Members with Stats", color=colors.NEUTRAL)
            embed.set_author(name=f"{company['name']} | {company['tag']}", icon_url=company['icon'] if company['icon'] else None)
            for name, stat in members_stats[i:i + entries_per_page]:
                embed.add_field(name=name, value=stat, inline=True)
                embed.set_footer(text=f"Page: {page_number}/{total_pages} ({len(members_stats)} entries)")
                embeds.append(embed)
        return await ctx.paginator(embeds)

    @company_members.command(name="list")
    @create_account()
    async def company_members_list(self, ctx: EvelinaContext):
        """List all members of your company with their ranks"""
        company = await self.economy.get_user_company(ctx.author.id)
        if not company:
            return await ctx.send_warning("You are not in a company.")
        roles = company.get('roles', {})
        if isinstance(roles, str):
            roles = json.loads(roles)
        ranks = {
            company['ceo']: "CEO",
            **{user_id: "Manager" for user_id in roles.get('Manager', [])},
            **{user_id: "Senior" for user_id in roles.get('Senior', [])},
        }
        rank_priority = {"CEO": 1, "Manager": 2, "Senior": 3, "Employee": 4}
        sorted_members = sorted(company['members'], key=lambda x: rank_priority.get(ranks.get(x, "Employee")))
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
        embed.set_author(name=f"{company['name']} | {company['tag']}", icon_url=company['icon'] if company['icon'] else None)
        for rank, members in members_by_rank.items():
            if members:
                embed.add_field(name=f"{rank_emojis[rank]} {rank}", value=" ".join(members), inline=True)
            else:
                embed.add_field(name=f"{rank_emojis[rank]} {rank}", value="N/A", inline=True)
        return await ctx.send(embed=embed)

    @company.command(name="name", usage="company name monkeys")
    @create_account()
    async def company_name(self, ctx: EvelinaContext, *, name: ValidCompanyName):
        """Change your company's name"""
        company = await self.economy.get_user_company(ctx.author.id)
        if not company:
            return await ctx.send_warning("You are not in a company.")
        if await self.economy.get_user_rank(ctx.author.id) < 4:
            return await ctx.send_warning("You are **missing** the following permission: `CEO`")
        if company['vault'] < 1000000:
            return await ctx.send_warning(f"Company name change costs **1,000,000** {self.cash}")
        await self.bot.db.execute("UPDATE company SET name = $1, vault = vault - $2 WHERE ceo = $3", name, 1000000, ctx.author.id)
        return await ctx.send_success(f"Company name successfully changed to **{name}**")
    
    @company.command(name="description", usage="company description monkeys are cool")
    @create_account()
    async def company_description(self, ctx: EvelinaContext, *, description: ValidCompanyDescription):
        """Change your company's description"""
        company = await self.economy.get_user_company(ctx.author.id)
        if not company:
            return await ctx.send_warning("You are not in a company.")
        if await self.economy.get_user_rank(ctx.author.id) < 3:
            return await ctx.send_warning("You are **missing** the following permission: `CEO` or `Manager`")
        await self.bot.db.execute("UPDATE company SET description = $1 WHERE ceo = $2", description, ctx.author.id)
        return await ctx.send_success(f"Company description successfully changed to:\n```{description}```")

    @company.command(name="tag", usage="company tag MNKY")
    @create_account()
    async def company_tag(self, ctx: EvelinaContext, tag: ValidCompanyTag):
        """Change your company's tag"""
        company = await self.economy.get_user_company(ctx.author.id)
        if not company:
            return await ctx.send_warning("You are not in a company.")
        if await self.economy.get_user_rank(ctx.author.id) < 4:
            return await ctx.send_warning("You are **missing** the following permission: `CEO`")
        if company['vault'] < 500000:
            return await ctx.send_warning(f"Company tag change costs **500,000** {self.cash}")
        await self.bot.db.execute("UPDATE company SET tag = $1, vault = vault - $2 WHERE ceo = $3", str(tag).upper(), 500000, ctx.author.id)
        return await ctx.send_success(f"Company tag successfully changed to **{str(tag).upper()}**")
    
    @company.command(name="icon", usage="company icon [attachment|link]")
    @create_account()
    async def company_icon(self, ctx: EvelinaContext, icon: str = None):
        """Change your company's icon"""
        company = await self.economy.get_user_company(ctx.author.id)
        if not company:
            return await ctx.send_warning("You are not in a company.")
        if await self.economy.get_user_rank(ctx.author.id) < 4:
            return await ctx.send_warning("You are **missing** the following permission: `CEO`")
        valid_extensions = ['png', 'jpg', 'jpeg', 'gif']
        if ctx.message.attachments:
            attachment = ctx.message.attachments[0]
            file_extension = attachment.filename.split('.')[-1].lower()
            if file_extension not in valid_extensions:
                return await ctx.send_warning("Invalid file type. Please upload a valid image `png`, `jpg`, `jpeg` or `gif`")
            file_name = f"{str(uuid.uuid4())[:8]}.{file_extension}"
            response = await self.bot.session.get_bytes(attachment.url)
            if response:
                file_data = BytesIO(response)
                content_type = attachment.content_type
                await self.bot.r2.upload_file("evelina", file_data, file_name, content_type, "company")
                file_url = f"https://cdn.evelina.bot/company/{file_name}"
                await self.bot.db.execute("UPDATE company SET icon = $1 WHERE ceo = $2", file_url, ctx.author.id)
                return await ctx.send_success(f"Company icon successfully changed to [{file_name}]({file_url})")
        elif icon:
            file_extension = icon.split('?')[0].split('.')[-1].lower()
            if file_extension not in valid_extensions:
                return await ctx.send_warning("Invalid file type. Please provide a valid image URL (png, jpg, jpeg, gif).")
            await self.bot.db.execute("UPDATE company SET icon = $1 WHERE ceo = $2", icon, ctx.author.id)
            return await ctx.send_success(f"Company icon successfully changed to {icon}")
        else:
            return await ctx.send_warning("You must provide an attachment or a link to an image")

    @company.command(name="upgrade")
    @create_account()
    async def company_upgrade(self, ctx: EvelinaContext):
        """Upgrade your company"""
        company = await self.economy.get_user_company(ctx.author.id)
        if not company:
            return await ctx.send_warning("You are not in a company.")
        if await self.economy.get_user_rank(ctx.author.id) < 4:
            return await ctx.send_warning("You are **missing** the following permission: `CEO`")
        upgrade_data = await self.bot.db.fetchrow("SELECT * FROM company_upgrades WHERE level = $1", company['level'] + 1)
        if not upgrade_data:
            return await ctx.send_warning("Your company is already at the maximum level.")
        if company['vault'] < upgrade_data['cost']:
            return await ctx.send_warning(f"You do not have enough cash to upgrade your company\n> You need **{self.bot.misc.humanize_number(upgrade_data['cost'])}** {self.cash}")
        if company['reputation'] < upgrade_data['reputation']:
            return await ctx.send_warning(f"You do not have enough reputation to upgrade your company\n> You need **{upgrade_data['reputation']}** reputation")
        await self.bot.db.execute("UPDATE company SET level = level + 1, vault = vault - $1  WHERE ceo = $2", upgrade_data['cost'], ctx.author.id)
        return await ctx.send_success(f"Your company has been successfully upgraded to level **{company['level'] + 1}**")
        
    @company.group(name="leaderboard", aliases=["lb"], invoke_without_command=True, case_insensitive=True)
    @create_account()
    async def company_leaderboard(self, ctx: EvelinaContext):
        """View the company leaderboard"""
        return await ctx.create_pages()
    
    @company_leaderboard.command(name="reputation", aliases=["rep"])
    @create_account()
    async def company_leaderboard_reputation(self, ctx: EvelinaContext):
        """View the company leaderboard by reputation"""
        results = await self.bot.db.fetch("SELECT name, tag, reputation FROM company ORDER BY reputation DESC")
        if not results:
            return await ctx.send_warning("No companies found in the database.")
        leaderboard_entries = [f"**{result['name']} | {result['tag']}** - {result['reputation']} reputation" for index, result in enumerate(results)]
        return await ctx.paginate(leaderboard_entries, "Company Reputation Leaderboard", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})
    
    @company_leaderboard.command(name="votes")
    @create_account()
    async def company_leaderboard_votes(self, ctx: EvelinaContext):
        """View the company leaderboard by votes"""
        results = await self.bot.db.fetch("SELECT id, name, tag FROM company")
        if not results:
            return await ctx.send_warning("No companies found in the database.")
        leaderboard_entries = []
        for result in results:
            total_votes = await self.bot.db.fetchval("SELECT COALESCE(SUM(votes), 0) FROM company_voters WHERE company_id = $1", result['id'])
            leaderboard_entries.append(f"**{result['name']} | {result['tag']}** - {total_votes} votes")
        leaderboard_entries.sort(key=lambda x: int(x.split('- ')[1].split()[0]), reverse=True)
        return await ctx.paginate(leaderboard_entries, "Company Votes Leaderboard", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @company_leaderboard.command(name="vault")
    @create_account()
    async def company_leaderboard_vault(self, ctx: EvelinaContext):
        """View the company leaderboard by vault"""
        results = await self.bot.db.fetch("SELECT name, tag, vault FROM company ORDER BY vault DESC")
        if not results:
            return await ctx.send_warning("No companies found in the database.")
        leaderboard_entries = [f"**{result['name']} | {result['tag']}** - {self.bot.misc.humanize_number(result['vault'])} {self.cash}" for result in results]
        return await ctx.paginate(leaderboard_entries, "Company Vault Leaderboard", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @company_leaderboard.command(name="networth", aliases=["nw"])
    @create_account()
    async def company_leaderboard_networth(self, ctx: EvelinaContext):
        """View the company leaderboard by networth"""
        results = await self.bot.db.fetch("SELECT name, tag, members FROM company")
        if not results:
            return await ctx.send_warning("No companies found in the database.")
        leaderboard_entries = []
        for result in results:
            networth = sum(await asyncio.gather(*(self.economy.get_user_networth(member_id) for member_id in result['members'] if member_id)))
            leaderboard_entries.append(f"**{result['name']} | {result['tag']}** - {self.bot.misc.humanize_number(networth)} {self.cash}")
        leaderboard_entries.sort(key=lambda x: float(x.split('- ')[1].split()[0].replace(",", "")), reverse=True)
        return await ctx.paginate(leaderboard_entries, "Company Networth Leaderboard", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @company.command(name="privacy", usage="company privacy request")
    @create_account()
    async def company_privacy(self, ctx: EvelinaContext, *, privacy: str):
        """Change your company's privacy settings"""
        company = await self.economy.get_user_company(ctx.author.id)
        if not company:
            return await ctx.send_warning("You are not in a company.")
        if not await self.economy.get_user_rank(ctx.author.id) in [3, 4]:
            return await ctx.send_warning("You are **missing** the following permission: `CEO` or `Manager`")
        if privacy not in ['public', 'request', 'closed']:
            return await ctx.send_warning("Invalid privacy setting. Choose between `public`, `request` or `closed`")
        await self.bot.db.execute("UPDATE company SET privacy = $1 WHERE ceo = $2", privacy, ctx.author.id)
        await ctx.send_success(f"Company privacy successfully changed to **{privacy}**")

    @company.command(name="join", usage="company join addicted")
    @create_account()
    async def company_join(self, ctx: EvelinaContext, *, name: str):
        """Join a company"""
        user_company = await self.economy.get_user_company(ctx.author.id)
        if user_company:
            return await ctx.send_warning("You are already in a company.")
        company = await self.economy.get_company(name)
        if not company:
            company = await self.economy.get_tag_company(name)
            if not company:
                return await ctx.send_warning("Company with this name does not exist.")
        if company['privacy'] == 'closed':
            return await ctx.send_warning("This company is closed and can't be joined.")
        if company['privacy'] == 'request':
            return await ctx.send_warning(f"This company requires a request to join.\n> Use `{ctx.clean_prefix}company request {name}` to send a request.")
        limits = await self.economy.get_level_info(company['level'])
        if len(company["members"]) >= limits['members']:
            return await ctx.send_warning(f"Company is already at the maximum member limit of **{limits['members']}**")
        await self.bot.db.execute("UPDATE company SET members = array_append(members, $1) WHERE name = $2", ctx.author.id, company['name'])
        return await ctx.send_success(f"Successfully joined the company **{company['name']}**")

    @company.command(name="leave")
    @create_account()
    async def company_leave(self, ctx: EvelinaContext):
        """Leave your company"""
        company = await self.economy.get_user_company(ctx.author.id)
        if not company:
            return await ctx.send_warning("You are not in a company.")
        if await self.economy.get_user_rank(ctx.author.id) == 4:
            return await ctx.send_warning("You can't leave the company as the CEO. Transfer ownership or disband the company.")
        roles = json.loads(company.get('roles', '{}'))
        user_rank = await self.economy.get_user_rank(ctx.author.id)
        if user_rank == 3:
            roles.get('Manager', []).remove(ctx.author.id)
        elif user_rank == 2:
            roles.get('Senior', []).remove(ctx.author.id)
        await self.bot.db.execute("UPDATE company SET members = array_remove(members, $1), roles = $2 WHERE id = $3", ctx.author.id, json.dumps(roles), company['id'])
        return await ctx.send_success(f"You have successfully left the company **{company['name']}**")

    @company.command(name="kick", usage="company kick comminate")
    @create_account()
    async def company_kick(self, ctx: EvelinaContext, user: User):
        """Kick a member from the company"""
        company = await self.economy.get_user_company(ctx.author.id)
        if not company:
            return await ctx.send_warning("You are not in a company.")
        if not await self.economy.get_user_rank(ctx.author.id) in [3, 4]:
            return await ctx.send_warning("You are **missing** the following permission: `CEO` or `Manager`")
        roles = json.loads(company.get('roles', '{}'))
        if user.id not in company["members"]:
            return await ctx.send_warning(f"{user.mention} is not in your company.")
        author_rank = await self.economy.get_user_rank(ctx.author.id)
        target_rank = await self.economy.get_user_rank(user.id)
        if target_rank == 4:
            return await ctx.send_warning("You can't kick the CEO.")
        if author_rank <= target_rank:
            return await ctx.send_warning("You can't kick someone with the same or higher rank.")
        await self.bot.db.execute("UPDATE company SET members = array_remove(members, $1) WHERE id = $2", user.id, company['id'])
        if target_rank == 3:
            roles.get('Manager', []).remove(user.id)
        elif target_rank == 2:
            roles.get('Senior', []).remove(user.id)
        await self.bot.db.execute("UPDATE company SET roles = $1 WHERE id = $2", json.dumps(roles), company['id'])
        return await ctx.send_success(f"{user.mention} has been kicked from the company.")

    @company.command(name="uprank", usage="company uprank comminate")
    @create_account()
    async def company_uprank(self, ctx: EvelinaContext, user: Member):
        """Promote a member within the company"""
        company = await self.economy.get_user_company(ctx.author.id)
        if not company:
            return await ctx.send_warning("You are not in a company.")
        roles = json.loads(company.get('roles', '{}'))
        if not await self.economy.get_user_rank(ctx.author.id) in [3, 4]:
            return await ctx.send_warning("You are **missing** the following permission: `CEO` or `Manager`")
        if user.id not in company["members"]:
            return await ctx.send_warning(f"{user.mention} is not in your company.")
        author_rank = await self.economy.get_user_rank(ctx.author.id)
        target_rank = await self.economy.get_user_rank(user.id)
        if author_rank <= target_rank:
            return await ctx.send_warning("You can't uprank someone with the same or higher rank.")
        if target_rank == 2:
            if await self.economy.get_user_rank(ctx.author.id) < 4:
                return await ctx.send_warning("You are **missing** the following permission: `CEO`")
            limit = await self.economy.get_level_info(company['level'])
            if len(roles.get('Manager', [])) >= limit['managers']:
                return await ctx.send_warning(f"Your company is already at the maximum Manager limit of **{limit['managers']}**")
            roles['Senior'].remove(user.id)
            roles.setdefault('Manager', []).append(user.id)
            new_rank = "Manager"
        elif target_rank == 1:
            roles.setdefault('Senior', []).append(user.id)
            new_rank = "Senior"
        else:
            return await ctx.send_warning("User cannot be promoted further.")
        await self.bot.db.execute("UPDATE company SET roles = $1 WHERE id = $2", json.dumps(roles), company['id'])
        return await ctx.send_success(f"{user.mention} has been promoted to **{new_rank}**.")

    @company.command(name="downrank", usage="company downrank comminate")
    @create_account()
    async def company_downrank(self, ctx: EvelinaContext, user: Member):
        """Demote a member within the company"""
        company = await self.economy.get_user_company(ctx.author.id)
        if not company:
            return await ctx.send_warning("You are not in a company.")
        roles = json.loads(company.get('roles', '{}'))
        if not await self.economy.get_user_rank(ctx.author.id) in [3, 4]:
            return await ctx.send_warning("You are **missing** the following permission: `CEO` or `Manager`")
        if user.id not in company["members"]:
            return await ctx.send_warning(f"{user.mention} is not in your company.")
        author_rank = await self.economy.get_user_rank(ctx.author.id)
        target_rank = await self.economy.get_user_rank(user.id)
        if target_rank == 1:
            return await ctx.send_warning(f"{user.mention} is already an **Employee** and can't be downranked further.")
        if author_rank <= target_rank:
            return await ctx.send_warning("You can't downrank someone with the same or higher rank.")
        if target_rank == 3:
            roles['Manager'].remove(user.id)
            roles.setdefault('Senior', []).append(user.id)
            new_rank = "Senior"
        elif target_rank == 2:
            roles['Senior'].remove(user.id)
            new_rank = "Employee"
        else:
            return await ctx.send_warning("User can't be demoted further.")
        await self.bot.db.execute("UPDATE company SET roles = $1 WHERE id = $2", json.dumps(roles), company['id'])
        return await ctx.send_success(f"{user.mention} has been demoted to **{new_rank}**.")

    @company.command(name="requests")
    @create_account()
    async def company_requests(self, ctx: EvelinaContext):
        """View all pending join requests for your company"""
        company = await self.economy.get_user_company(ctx.author.id)
        if not company:
            return await ctx.send_warning("You are not in a company.")
        roles = company.get('roles', {})
        if isinstance(roles, str):
            roles = json.loads(roles)
        if not await self.economy.get_user_rank(ctx.author.id) in [2, 3, 4]:
            return await ctx.send_warning("You are **missing** the following permission: `CEO`, `Manager` or `Senior`")
        requests = await self.bot.db.fetch("SELECT user_id, created, text FROM company_requests WHERE company_id = $1", company['id'])
        if not requests:
            return await ctx.send_warning("There are no pending requests.")
        view = RequestView(ctx, requests, company, self.bot)
        embed = Embed(title=f"Join Requests", color=colors.NEUTRAL)
        embed.set_author(name=f"{company['name']} | {company['tag']}", icon_url=company['icon'] if company['icon'] else None)
        embed.add_field(name="User", value=f"<@{requests[0]['user_id']}>", inline=True)
        embed.add_field(name="Networth", value=f"{self.bot.misc.humanize_number(await self.economy.get_user_networth(requests[0]['user_id']))} {self.cash}", inline=True)
        embed.add_field(name="Created", value=f"<t:{requests[0]['created']}:f>", inline=True)
        embed.add_field(name="Application", value=f"```{requests[0]['text'] if requests[0]['text'] else 'N/A'}```", inline=False)
        embed.set_footer(text=f"Page: 1/{len(requests)} ({len(requests)} entries)")
        return await ctx.send(embed=embed, view=view)

    @company.command(name="request", usage="company request addicted I am rich")
    @create_account()
    async def company_request(self, ctx: EvelinaContext, name: str, *, text: str):
        """Send a request to join a company or cancel an active request"""
        user_company = await self.economy.get_user_company(ctx.author.id)
        if user_company:
            return await ctx.send_warning("You are already in a company.")
        company = await self.economy.get_company(name)
        if not company:
            company = await self.economy.get_tag_company(name)
            if not company:
                return await ctx.send_warning("Company with this name does not exist.")
        pending_request = await self.economy.get_pending_request(ctx.author.id, company['id'])
        if text.lower() == "cancel":
            if not pending_request:
                return await ctx.send_warning("You have no active join request.")
            await self.bot.db.execute("DELETE FROM company_requests WHERE user_id = $1 AND company_id", ctx.author.id, company['id'])
            return await ctx.send_success("Successfully cancelled your join request.")
        if pending_request:
            return await ctx.send_warning(f"You already have a pending join request for **{company['name']}**")
        if company['privacy'] == 'closed':
            return await ctx.send_warning("This company is closed and can't be joined.")
        if company['privacy'] == 'public':
            return await ctx.send_warning("This company is public, you can join directly.")
        limits = await self.economy.get_level_info(company['level'])
        if len(company["members"]) >= limits['members']:
            return await ctx.send_warning(f"Company is already at the maximum member limit of **{limits['members']}**")
        await self.bot.db.execute("INSERT INTO company_requests (user_id, company_id, text, created) VALUES ($1, $2, $3, $4)", ctx.author.id, company['id'], text, datetime.datetime.now().timestamp())
        await ctx.send_success(f"Successfully sent a request to join the company **{name}**")

    @company.command(name="invite", usage="company invite comminate")
    @create_account()
    async def company_invite(self, ctx: EvelinaContext, user: User):
        """Invite a user to join your company"""
        company = await self.economy.get_user_company(ctx.author.id)
        if not company:
            return await ctx.send_warning("You are not in a company.")
        target_company = await self.economy.get_user_company(user.id)
        if target_company:
            if target_company['id'] == company['id']:
                return await ctx.send_warning(f"{user.mention} is already in your company.")
            else:
                return await ctx.send_warning(f"{user.mention} is already in a company.")
        if not await self.economy.get_user_rank(ctx.author.id) in [2, 3, 4]:
            return await ctx.send_warning("You are **missing** the following permission: `CEO`, `Manager` or `Senior`")
        pending_invites = await self.economy.get_pending_invites(user.id, company['id'])
        if pending_invites:
            return await ctx.send_warning(f"{user.mention} already has a pending invite request for your company.")
        try:
            embed = Embed(description=f"{emojis.QUESTION} You have been invited by {ctx.author.mention} to join the company **{company['name']}**", color=colors.NEUTRAL)
            view = InviteView(self.bot)
            msg = await user.send(embed=embed, view=view)
        except Exception:
            return await ctx.send_warning(f"{user.mention} has disabled DMs and can't be invited.")
        await self.bot.db.execute("INSERT INTO company_invites (user_id, company_id, message_id, created) VALUES ($1, $2, $3, $4)", user.id, company['id'], msg.id, datetime.datetime.now().timestamp())
        return await ctx.send_success(f"Successfully sent an invite to {user.mention}")    

    @company.command(name="uninvite", usage="company uninvite comminate")
    @create_account()
    async def company_uninvite(self, ctx: EvelinaContext, user: User):
        """Uninvite a user from joining your company"""
        company = await self.economy.get_user_company(ctx.author.id)
        if not company:
            return await ctx.send_warning("You are not in a company.")
        if not await self.economy.get_user_rank(ctx.author.id) in [2, 3, 4]:
            return await ctx.send_warning("You are **missing** the following permission: `CEO`, `Manager` or `Senior`")
        pending_invites = await self.economy.get_pending_invites(user.id, company['id'])
        if not pending_invites:
            return await ctx.send_warning(f"{user.mention} does not have a pending invite request for your company.")
        await self.bot.db.execute("DELETE FROM company_invites WHERE user_id = $1 AND company_id = $2", user.id, company['id'])
        return await ctx.send_success(f"Successfully uninvited {user.mention}")

    @company.group(name="vault", invoke_without_command=True, case_insensitive=True)
    @create_account()
    async def company_vault(self, ctx: EvelinaContext):
        """Manage your company vault"""
        return await ctx.create_pages()

    @company_vault.command(name="deposit", aliases=["dep"], usage="company vault deposit 1000000")
    @create_account()
    async def company_vault_deposit(self, ctx: EvelinaContext, amount: VaultDepositAmount):
        """Deposit cash into your company vault"""
        company = await self.economy.get_user_company(ctx.author.id)
        if not company:
            return await ctx.send_warning("You are not in a company.")
        await self.economy.deposit_vault(company, ctx.author, amount, "deposit")
        await self.quests.add_deposit_money(ctx.author, "vault", Decimal(amount))
        await self.economy.logging(ctx.author, Decimal(amount), "deposit", "vault")
        return await ctx.send_success(f"Successfully deposited **{self.bot.misc.humanize_number(amount)}** {self.cash} into the company vault.")
    
    @company_vault.command(name="withdraw", aliases=["with"], usage="company vault withdraw 1000000")
    @create_account()
    async def company_vault_withdraw(self, ctx: EvelinaContext, amount: VaultWithdrawAmount):
        """Withdraw cash from your company vault"""
        company = await self.economy.get_user_company(ctx.author.id)
        if not company:
            return await ctx.send_warning("You are not in a company.")
        if not await self.economy.get_user_rank(ctx.author.id) in [4]:
            return await ctx.send_warning("You are **missing** the following permission: `CEO`")
        if await self.economy.get_user_rank(ctx.author.id) == 3:
            if float(company['vault_limit']) > 0:
                check = await self.bot.db.fetchrow("SELECT * FROM company_limit_withdraw WHERE user_id = $1 AND date = $2", ctx.author.id, datetime.datetime.now(datetime.timezone.utc).date())
                if check:
                    limit = company['vault_limit'] - check['spent']
                else:
                    limit = company['vault_limit']
                if amount > limit:
                    return await ctx.send_warning(f"You reached daily vault withdraw limit. You can withdraw **{self.bot.misc.humanize_number(limit)}** {self.cash} today!")
        await self.economy.withdraw_vault(company, ctx.author, amount, "withdraw")
        await self.economy.logging(ctx.author, Decimal(amount), "withdraw", "vault")
        await self.bot.db.execute("INSERT INTO company_limit_withdraw (user_id, spent, date) VALUES ($1, $2, $3) ON CONFLICT (user_id, date) DO UPDATE SET spent = company_limit_withdraw.spent + $2", ctx.author.id, amount, datetime.datetime.now(datetime.timezone.utc).date())
        return await ctx.send_success(f"Successfully withdrew **{self.bot.misc.humanize_number(amount)}** {self.cash} from the company vault.")

    @company_vault.command(name="bonus", usage="company vault bonus comminate 1000000")
    @create_account()
    async def company_vault_bonus(self, ctx: EvelinaContext, user: User, amount: VaultWithdrawAmount):
        """Send a bonus to a user from your company vault"""
        company = await self.economy.get_user_company(ctx.author.id)
        if not company:
            return await ctx.send_warning("You are not in a company.")
        if not await self.economy.get_user_rank(ctx.author.id) in [4]:
            return await ctx.send_warning("You are **missing** the following permission: `CEO`")
        if user.id not in company["members"]:
            return await ctx.send_warning(f"{user.mention} is not in your company.")
        limit = await self.economy.get_level_info(company['level'])
        check = await self.bot.db.fetchrow("SELECT * FROM company_limit_bonus WHERE user_id = $1 AND date = $2", user.id, datetime.datetime.now(datetime.timezone.utc).date())
        if check:
            limit = limit['bonus'] - check['spent']
        else:
            limit = limit['bonus']
        if amount > limit:
            return await ctx.send_warning(f"You reached daily vault bonus limit. You can send **{self.bot.misc.humanize_number(limit)}** {self.cash} bonus today!")
        await self.economy.withdraw_vault(company, user, amount, "bonus")
        await self.economy.logging(ctx.author, Decimal(amount), "bonus", "vault")
        await self.bot.db.execute("INSERT INTO company_limit_bonus (user_id, spent, date) VALUES ($1, $2, $3) ON CONFLICT (user_id, date) DO UPDATE SET spent = company_limit_bonus.spent + $2", user.id, amount, datetime.datetime.now(datetime.timezone.utc).date())
        return await ctx.send_success(f"Successfully sent a bonus of **{self.bot.misc.humanize_number(amount)}** {self.cash} to {user.mention}")

    @company_vault.command(name="limit", usage="company vault limit 1000000")
    @create_account()
    async def company_vault_limit(self, ctx: EvelinaContext, amount: Amount):
        """Set the company vault limit"""
        company = await self.economy.get_user_company(ctx.author.id)
        if not company:	
            return await ctx.send_warning("You are not in a company.")
        if not await self.economy.get_user_rank(ctx.author.id) == 4:
            return await ctx.send_warning("You are **missing** the following permission: `CEO`")
        await self.bot.db.execute("UPDATE company SET vault_limit = $1 WHERE id = $2", amount, company['id'])
        return await ctx.send_success(f"Company vault limit successfully set to **{self.bot.misc.humanize_number(amount)}** {self.cash}")

    @company_vault.command(name="logs", aliases=["history"])
    @create_account()
    async def company_vault_logs(self, ctx: EvelinaContext):
        """View the company vault logs"""
        company = await self.economy.get_user_company(ctx.author.id)
        if not company:
            return await ctx.send_warning("You are not in a company.")
        logs = await self.bot.db.fetch("SELECT * FROM company_vault WHERE company_id = $1 ORDER BY created DESC", company['id'])
        if not logs:
            return await ctx.send_warning("No logs found in the database.")
        content = []
        for log in logs:
            content.append(f"**{str(log['type']).capitalize()}** by <@{log['user_id']}> | {self.bot.misc.humanize_number(log['amount'])} {self.cash} - <t:{log['created']}:f>")
        return await ctx.paginate(content, "Vault Transactions", {"name": f"{company['name']} | {company['tag']}", "icon_url": company['icon'] if company['icon'] else None})

    @company.group(name="project", invoke_without_command=True, case_insensitive=True)
    @create_account()
    async def company_project(self, ctx: EvelinaContext):
        """Manage your company projects"""
        return await ctx.create_pages()

    @company_project.command(name="start", usage="company project start Apartment")
    @create_account()
    async def company_project_start(self, ctx: EvelinaContext, *, name: str):
        """Start a project for your company"""
        company = await self.economy.get_user_company(ctx.author.id)
        if not company:
            return await ctx.send_warning("You are not in a company.")
        company_project = await self.bot.db.fetchrow("SELECT * FROM company_projects_started WHERE company_id = $1 AND active = $2", company['id'], True)
        if company_project:
            return await ctx.send_warning("You already have an active project.")
        if not await self.economy.get_user_rank(ctx.author.id) in [3, 4]:
            return await ctx.send_warning("You are **missing** the following permission: `CEO` or `Manager`")
        project = await self.bot.db.fetchrow("SELECT * FROM company_projects WHERE LOWER(name) = LOWER($1)", name)
        if not project:
            return await ctx.send_warning("Project with this name does not exist.")
        if company['level'] < project['group']:
            return await ctx.send_warning(f"Your company is not at the required level to start this project")
        await self.bot.db.execute("INSERT INTO company_projects_started (company_id, project_name, money, votes, active, participant, created) VALUES ($1, $2, 0, 0, $3, $4, $5)", company['id'], project['name'], True, "{}", datetime.datetime.now().timestamp())
        return await ctx.send_success(f"Successfully started the project **{project['name']}**")

    @company_project.command(name="cancel", aliases=["stop"])
    @create_account()
    async def company_project_cancel(self, ctx: EvelinaContext):
        """Cancel your company project"""
        company = await self.economy.get_user_company(ctx.author.id)
        if not company:
            return await ctx.send_warning("You are not in a company.")
        company_project = await self.bot.db.fetchrow("SELECT * FROM company_projects_started WHERE company_id = $1 AND active = $2", company['id'], True)
        if not company_project:
            return await ctx.send_warning("You don't have an active project.")
        if not await self.economy.get_user_rank(ctx.author.id) in [3, 4]:
            return await ctx.send_warning("You are **missing** the following permission: `CEO` or `Manager`")
        await self.bot.db.execute("UPDATE company_projects_started SET active = $1 WHERE company_id = $2 AND active = $3", False, company['id'], True)
        return await ctx.send_success("Successfully cancelled the project.")

    @company_project.command(name="status")
    @create_account()
    async def company_project_status(self, ctx: EvelinaContext):
        """View the status of your company project"""
        company = await self.economy.get_user_company(ctx.author.id)
        if not company:
            return await ctx.send_warning("You are not in a company.")
        company_project = await self.bot.db.fetchrow("SELECT * FROM company_projects_started WHERE company_id = $1 AND active = $2", company['id'], True)
        if not company_project:
            return await ctx.send_warning("You don't have an active project.")
        project = await self.bot.db.fetchrow("SELECT * FROM company_projects WHERE name = $1", company_project['project_name'])
        if not project:
            return await ctx.send_warning("Project with this name does not exist.")
        total_money = self.bot.misc.humanize_number(company_project['money'])
        needed_money = self.bot.misc.humanize_number(project['cost'])
        total_votes = self.bot.misc.humanize_clean_number(company['votes'])
        needed_votes = self.bot.misc.humanize_clean_number(project['votes'])
        embed = Embed(title=f"{project['name']} {project['emoji']}", description=project['description'], color=colors.NEUTRAL)
        embed.add_field(name="Cost", value=f"{total_money}/{needed_money}", inline=True)
        embed.add_field(name="Votes", value=f"{total_votes}/{needed_votes}", inline=True)
        embed.set_image(url=project['image'])
        return await ctx.send(embed=embed)

    @company_project.command(name="contribute", aliases=["cont"], usage="company project contribute 1000000")
    @create_account()
    async def company_project_contribute(self, ctx: EvelinaContext, amount: ProjectContributeAmount):
        """Contribute to your company project"""
        company = await self.economy.get_user_company(ctx.author.id)
        if not company:
            return await ctx.send_warning("You are not in a company.")
        company_project = await self.bot.db.fetchrow("SELECT * FROM company_projects_started WHERE company_id = $1 AND active = $2", company['id'], True)
        if not company_project:
            return await ctx.send_warning("You don't have an active project.")
        project = await self.bot.db.fetchrow("SELECT * FROM company_projects WHERE name = $1", company_project['project_name'])
        if not project:
            return await ctx.send_warning("Project with this name does not exist.")
        
        

        participants = json.loads(company_project['participant'])
        participants[str(ctx.author.id)] = participants.get(str(ctx.author.id), 0) + amount
        await self.bot.db.execute("UPDATE company_projects_started SET money = money + $1, participant = $2 WHERE company_id = $3 AND active = $4", amount, json.dumps(participants), company['id'], True)
        await self.bot.db.execute("UPDATE economy SET cash = cash - $1 WHERE user_id = $2", amount, ctx.author.id)
        await self.economy.logging(ctx.author, Decimal(amount), "contribute", "project")
        return await ctx.send_success(f"Successfully contributed **{self.bot.misc.humanize_number(amount)}** {self.cash} to the project **{company_project['project_name']}**")

    @company_project.command(name="participants", aliases=["part"])
    @create_account()
    async def company_project_participants(self, ctx: EvelinaContext):
        """View the participants of your company project"""
        company = await self.economy.get_user_company(ctx.author.id)
        if not company:
            return await ctx.send_warning("You are not in a company.")
        company_project = await self.bot.db.fetchrow("SELECT * FROM company_projects_started WHERE company_id = $1 AND active = $2", company['id'], True)
        if not company_project:
            return await ctx.send_warning("You don't have an active project.")
        project = await self.bot.db.fetchrow("SELECT * FROM company_projects WHERE name = $1", company_project['project_name'])
        if not project:
            return await ctx.send_warning("Project with this name does not exist.")
        participants = json.loads(company_project['participant'])
        if not participants:
            return await ctx.send_warning("No participants found.")
        content = []
        for user_id, amount in participants.items():
            user = self.bot.get_user(int(user_id)) or await self.bot.fetch_user(int(user_id))
            if user:
                content.append(f"**{user}** - {self.bot.misc.humanize_number(amount)} {self.cash}")
        return await ctx.paginate(content, f"Participants of {company_project['project_name']}", {"name": f"{company['name']} | {company['tag']}", "icon_url": company['icon'] if company['icon'] else None})

    @company_project.command(name="complete")
    @create_account()
    async def company_project_complete(self, ctx: EvelinaContext):
        """Complete your company project"""
        company = await self.economy.get_user_company(ctx.author.id)
        if not company:
            return await ctx.send_warning("You are not in a company.")
        company_project = await self.bot.db.fetchrow("SELECT * FROM company_projects_started WHERE company_id = $1 AND active = $2", company['id'], True)
        if not company_project:
            return await ctx.send_warning("You don't have an active project.")
        project = await self.bot.db.fetchrow("SELECT * FROM company_projects WHERE name = $1", company_project['project_name'])
        if not project:
            return await ctx.send_warning("Project with this name does not exist.")
        if company_project['money'] < project['cost']:
            return await ctx.send_warning("You have not reached the required amount of **money** to complete the project.")
        if company['votes'] < project['votes']:
            return await ctx.send_warning("You have not reached the required amount of **votes** to complete the project.")
        await self.bot.db.execute("UPDATE company_projects_started SET active = $1 WHERE company_id = $2", False, company['id'])
        await self.bot.db.execute("UPDATE company SET reputation = reputation + $1, votes = votes - $2 WHERE id = $3", project['reputation'], project['votes'], company['id'])
        await self.economy.add_vault(company, ctx.author, project['earnings'] - project['cost'], "project completion")
        participants = json.loads(company_project['participant'])
        for user_id, amount in participants.items():
            earnings = project['earnings'] * (amount / project['cost'])
            check = await self.bot.db.fetchrow("SELECT * FROM company_earnings WHERE company_id = $1 AND user_id = $2", company['id'], int(user_id))
            if not check:
                await self.bot.db.execute("INSERT INTO company_earnings (user_id, company_id, amount) VALUES ($1, $2, $3)", int(user_id), company['id'], earnings)
            else:
                await self.bot.db.execute("UPDATE company_earnings SET amount = amount + $1 WHERE company_id = $2 AND user_id = $3", earnings, company['id'], int(user_id))
        return await ctx.send_success(f"Successfully completed the project **{company_project['project_name']}** and earned **{self.bot.misc.humanize_number(project['earnings'])}** {self.cash} + {project['reputation']} Reputation")

    @company_project.command(name="collect", usage="company project collect 1000000")
    @create_account()
    async def company_project_collect(self, ctx: EvelinaContext, amount: ProjectCollectAmount):
        """Collect your company project earnings"""
        company = await self.economy.get_user_company(ctx.author.id)
        if not company:
            return await ctx.send_warning("You are not in a company.")
        earnings = await self.bot.db.fetchrow("SELECT * FROM company_earnings WHERE company_id = $1 AND user_id = $2", company['id'], ctx.author.id)
        if not earnings:
            return await ctx.send_warning("You have no earnings to collect.")
        if earnings['amount'] < amount:
            return await ctx.send_warning("You don't have enough earnings to collect.")
        await self.bot.db.execute("UPDATE company_earnings SET amount = amount - $1 WHERE company_id = $2 AND user_id = $3", amount, company['id'], ctx.author.id)
        await self.bot.db.execute("UPDATE economy SET cash = cash + $1 WHERE user_id = $2", amount, ctx.author.id)
        await self.economy.logging(ctx.author, Decimal(amount), "collect", "project")
        return await ctx.send_success(f"Successfully collected **{self.bot.misc.humanize_number(amount)}** {self.cash} from your company project earnings.")

    @company_project.command(name="list")
    @create_account()
    async def company_project_list(self, ctx: EvelinaContext):
        """List all projects that exist"""
        results = await self.bot.db.fetch("SELECT * FROM company_projects ORDER BY cost ASC")
        if not results:
            return await ctx.send_warning("No projects found in the database.")
        embeds = []
        for result in results:
            group = ["A", "B", "C", "D"][result['group'] - 1]
            embed = Embed(title=f"{result['name']} {result['emoji']} | {group}", description=result['description'], color=colors.NEUTRAL)
            embed.add_field(name="Cost", value=f"{self.bot.misc.humanize_number(result['cost'])} {self.cash}\n{result['votes']} Votes", inline=True)
            embed.add_field(name="Revenue", value=f"{self.bot.misc.humanize_number(result['earnings'])} {self.cash}\n{result['reputation']} Reputation", inline=True)
            embed.add_field(name="Profit", value=f"{self.bot.misc.humanize_number(result['earnings'] - result['cost'])} {self.cash}\n{result['reputation']} Reputation", inline=True)
            embed.set_image(url=result['image'])
            embed.set_footer(text=f"Page: {results.index(result) + 1}/{len(results)} ({len(results)} entries)")
            embeds.append(embed)
        return await ctx.paginator(embeds)

    @group(name="quest", invoke_without_command=True, case_insensitive=True)
    @create_account()
    async def quest(self, ctx: EvelinaContext):
        """Manage your quests"""
        return await ctx.create_pages()
    
    @quest.command(name="start", usage="quest start easy")
    @create_account()
    @quest_taken()
    async def quest_start(self, ctx: EvelinaContext, difficulty: str):
        """Start a quest"""
        if not difficulty.lower() in ["easy", "medium", "hard"]:
            return await ctx.send_warning("Invalid difficulty. Choose between `easy`, `medium` or `hard`")
        user_quest = await self.quests.get_user_quest(ctx.author)
        if user_quest:
            return await ctx.send_warning("You have an active quest.")
        random_quest = await self.quests.get_random_quest(difficulty)
        quest = await self.quests.get_quest(random_quest['id'])
        if quest:
            await self.bot.db.execute("INSERT INTO quests_user VALUES ($1, $2, $3, $4, $5)", ctx.author.id, quest['id'], quest['difficult'], 0, False)
            return await ctx.send_success(f"Successfully started the quest **{quest['name']}**, for completion you gain **{self.bot.misc.humanize_number(quest['earnings'])}** {self.cash}")
        else:
            return await ctx.send_warning("Your quest can't be found in the database")

    @quest.command(name="status", aliases=["info"])
    @create_account()
    async def quest_status(self, ctx: EvelinaContext):
        """View the status of your quest"""
        user_quest = await self.quests.get_user_quest(ctx.author)
        if not user_quest:
            return await ctx.send_warning("You don't have an active quest.")
        quest = await self.quests.get_quest(user_quest['id'])
        if quest:
            embed = Embed(title=quest['name'], color=colors.NEUTRAL)
            embed.add_field(name="Mode", value=str(quest['mode']).capitalize(), inline=True)
            embed.add_field(name="Difficulty", value=str(quest['difficult']).capitalize(), inline=True)
            embed.add_field(name="Progress", value=f"{user_quest['amount']:,}/{quest['amount']:,}", inline=True)
            return await ctx.send(embed=embed)
        else:
            return await ctx.send_warning("Your quest can't be found in the database")

    @quest.command(name="complete")
    @create_account()
    async def quest_complete(self, ctx: EvelinaContext):
        """Complete your quest"""
        user_quest = await self.quests.get_user_quest(ctx.author)
        if not user_quest:
            return await ctx.send_warning("You don't have an active quest.")
        quest = await self.quests.get_quest(user_quest['id'])
        if quest:
            if user_quest['amount'] < quest['amount']:
                return await ctx.send_warning("You have not completed the quest.")
            await self.bot.db.execute("UPDATE quests_user SET completed = $1 WHERE user_id = $2 AND id = $3", True, ctx.author.id, quest['id'])
            await self.bot.db.execute("UPDATE economy SET cash = cash + $1 WHERE user_id = $2", quest['earnings'], ctx.author.id)
            await self.economy.logging(ctx.author, Decimal(quest['earnings']), "collect", "quest")
            return await ctx.send_success(f"Successfully completed the quest **{quest['name']}** and gained **{self.bot.misc.humanize_number(quest['earnings'])}** {self.cash}")
        else:
            return await ctx.send_warning("Your quest can't be found in the database")

    @quest.command(name="stop", aliases=["delete"])
    @create_account()
    async def quest_stop(self, ctx: EvelinaContext):
        """Stop your quest"""
        user_quest = await self.quests.get_user_quest(ctx.author)
        if not user_quest:
            return await ctx.send_warning("You don't have an active quest.")
        quest = await self.quests.get_quest(user_quest['id'])
        if quest:
            async def yes_func(interaction: Interaction):
                await self.bot.db.execute("DELETE FROM quests_user WHERE user_id = $1 AND id = $2", ctx.author.id, quest['id'])
                await self.bot.db.execute("UPDATE economy SET quest = $1 WHERE user_id = $2", int((datetime.datetime.now() + datetime.timedelta(minutes=15)).timestamp()), ctx.author.id) 
                return await interaction.response.edit_message(embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Successfully cancelled the quest **{quest['name']}**"), view=None)
            async def no_func(interaction: Interaction):
                return await interaction.response.edit_message(embed=Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: Quest deletion got canceled"), view=None)
            return await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to **stop** your quest?\n> You have to wait **15 minutes** to start a new one!", yes_func, no_func)
        else:
            return await ctx.send_warning("Your quest can't be found in the database")

    @quest.command(name="leaderboard", aliases=["lb"])
    @create_account()
    async def quest_leaderboard(self, ctx: EvelinaContext):
        """View the quest leaderboard"""
        leaderboard = await self.bot.db.fetch("SELECT user_id, COUNT(*) as completed_quests FROM quests_user WHERE completed = TRUE GROUP BY user_id ORDER BY completed_quests DESC")
        if not leaderboard:
            return await ctx.send_warning("No entries found in the database.")
        content = []
        for entry in leaderboard:
            user = self.bot.get_user(entry['user_id']) or await self.bot.fetch_user(entry['user_id'])
            content.append(f"**{user}** - {entry['completed_quests']} completed quests")
        return await ctx.paginate(content, "Quest Leaderboard", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @group(name="investment", aliases=["invest"], invoke_without_command=True, case_insensitive=True)
    @create_account()
    async def investment(self, ctx: EvelinaContext):
        """Manage your investments"""
        return await ctx.create_pages()
    
    @investment.command(name="start", usage="investment start Startup")
    @create_account()
    async def investment_start(self, ctx: EvelinaContext, *, name: str):
        """Start an investment"""
        user_investment = await self.economy.get_user_investment(ctx.author.id)
        if user_investment:
            return await ctx.send_warning("You have an active investment.")
        investment = await self.economy.get_investment(name)
        if not investment:
            return await ctx.send_warning("Investment with this name does not exist.")
        cash = await self.bot.db.fetchval("SELECT cash FROM economy WHERE user_id = $1", ctx.author.id)
        if cash < investment['cost']:
            return await ctx.send_warning(f"You don't have enough cash to start this investment.\n> Required: **{self.bot.misc.humanize_number(investment['cost'])}** {self.cash}")
        await self.bot.db.execute("UPDATE economy SET cash = cash - $1 WHERE user_id = $2", investment['cost'], ctx.author.id)
        await self.bot.db.execute("INSERT INTO economy_investments_started VALUES ($1, $2, $3, $4)", investment['id'], ctx.author.id, datetime.datetime.now().timestamp(), True)
        return await ctx.send_success(f"Successfully started the investment **{investment['name']}**, for completion you gain **{self.bot.misc.humanize_number(investment['earnings'])}** {self.cash}")

    @investment.command(name="list")
    @create_account()
    async def investment_list(self, ctx: EvelinaContext):
        """List all investments that exist"""
        results = await self.bot.db.fetch("SELECT * FROM economy_investments ORDER BY cost ASC")
        if not results:
            return await ctx.send_warning("No investments found in the database.")
        embeds = []
        for result in results:
            embed = Embed(title=result['name'], description=result['description'], color=colors.NEUTRAL)
            embed.add_field(name="Cost", value=f"{self.bot.misc.humanize_number(result['cost'])} {self.cash}", inline=True)
            embed.add_field(name="Earnings", value=f"{self.bot.misc.humanize_number(result['earnings'])} {self.cash}", inline=True)
            embed.add_field(name="Days", value=result['days'], inline=True)
            embed.set_footer(text=f"Page: {results.index(result) + 1}/{len(results)} ({len(results)} entries)")
            embeds.append(embed)
        return await ctx.paginator(embeds)

    @investment.command(name="status", aliases=["info"])
    @create_account()
    async def investment_status(self, ctx: EvelinaContext):
        """View the status of your investment"""
        user_investment = await self.economy.get_user_investment(ctx.author.id)
        if not user_investment:
            return await ctx.send_warning("You don't have an active investment.")
        investment = await self.economy.get_id_investment((user_investment['id']))
        if investment:
            until_end_seconds = user_investment['timestamp'] + (investment['days'] * 86400)
            embed = Embed(title=investment['name'], color=colors.NEUTRAL)
            embed.add_field(name="Cost", value=f"{self.bot.misc.humanize_number(investment['cost'])} {self.cash}", inline=True)
            embed.add_field(name="Earnings", value=f"{self.bot.misc.humanize_number(investment['earnings'])} {self.cash}", inline=True)
            embed.add_field(name="Ends", value=f"<t:{until_end_seconds}:R>", inline=True)
            return await ctx.send(embed=embed)
        else:
            return await ctx.send_warning("Your investment can't be found in the database")
        
    @investment.command(name="complete")
    @create_account()
    async def investment_complete(self, ctx: EvelinaContext):
        """Complete your investment"""
        user_investment = await self.economy.get_user_investment(ctx.author.id)
        if not user_investment:
            return await ctx.send_warning("You don't have an active investment.")
        investment = await self.economy.get_id_investment(user_investment['id'])
        if investment:
            until_end_seconds = user_investment['timestamp'] + (investment['days'] * 86400)
            if until_end_seconds > datetime.datetime.now().timestamp():
                return await ctx.send_warning("Your investment has not ended yet\n> Ends: <t:" + str(until_end_seconds) + ":R>")
            await self.bot.db.execute("UPDATE economy SET cash = cash + $1 WHERE user_id = $2", investment['earnings'], ctx.author.id)
            await self.economy.logging(ctx.author, Decimal(investment['earnings']), "collect", "investment")
            await self.bot.db.execute("DELETE FROM economy_investments_started WHERE user_id = $1", ctx.author.id)
            return await ctx.send_success(f"Successfully completed the investment **{investment['name']}** and gained **{self.bot.misc.humanize_number(investment['earnings'])}** {self.cash}")
        else:
            return await ctx.send_warning("Your investment can't be found in the database")

async def setup(bot: Evelina) -> None:
    await bot.add_cog(Economy(bot))