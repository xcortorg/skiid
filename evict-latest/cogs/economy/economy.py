import discord
import time
import uuid
import config
import asyncio
import random
import json

from typing import Optional
from datetime import datetime, timezone, timedelta

from discord.ext import commands, tasks
from discord.ext.commands import max_concurrency, BucketType
from discord import Message, Embed, Member, Interaction

from core.client.context import Context
from main import Evict

# def is_econ_allowed():
#     async def predicate(ctx):
#         is_allowed = await ctx.bot.db.fetchval(
#             """SELECT EXISTS(
#                 SELECT 1 FROM economy_access 
#                 WHERE user_id = $1
#             )""", 
#             ctx.author.id
#         )
#         if not is_allowed:
#             await ctx.warn("You don't have access to economy commands yet, please read https://discord.com/channels/892675627373699072/1315003375296839741/1331888247860887582 in [the support server](https://discord.gg/evict)!")
#             return False
#         return True
#     return commands.check(predicate)

def is_econ_allowed():
    async def predicate(ctx):
        return True
    return commands.check(predicate)

class Economy(commands.Cog):
    def __init__(self, bot: Evict):
        self.bot = bot
        self.description = "Interact and play games with other users to earn coins and gems."

    async def eco_approve(self, ctx: Context, message: str) -> Message:
        embed = Embed(
            description=f"{config.EMOJIS.CONTEXT.APPROVE} {ctx.author.display_name}: {message}",
            color=discord.Color.green()
        )
        return await ctx.send(embed=embed)

    async def eco_deny(self, ctx: Context, message: str) -> Message:
        embed = Embed(
            description=f"{config.EMOJIS.CONTEXT.DENY} {ctx.author.display_name}: {message}",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    async def eco_warn(self, ctx: Context, message: str) -> Message:
        embed = Embed(
            description=f"{config.EMOJIS.CONTEXT.WARN} {ctx.author.display_name}: {message}",
            color=discord.Color.yellow()
        )
        return await ctx.send(embed=embed)

    async def eco_bank(self, ctx: Context, message: str) -> Message:
        embed = Embed(
            description=f"🏦 | {ctx.author.display_name}: {message}",
            color=0x2b2d31
        )
        return await ctx.send(embed=embed)

    async def cog_load(self):
        """
        Setup initial data like default shop items.
        """
        await self.setup_default_shop_items()

    async def cog_unload(self):
        """
        Cleanup any active games or temporary data.
        """
        pattern = "active_blackjack_games:*"
        keys = await self.bot.redis.keys(pattern)
        if keys:
            await self.bot.redis.delete(*keys)

    @staticmethod
    def calculate_multiplier(bombs: int, safe_revealed: int) -> float:
        """
        Calculate multiplier based on number of bombs and revealed safe squares.
        """
        base = 1 + (bombs * 0.15) 
        
        per_safe = 0.2 * (bombs / 8)  
        
        return base + (safe_revealed * per_safe)

    async def get_balance(self, user_id: int) -> tuple[int, int, int]:
        """
        Returns (wallet, bank, gems).
        """
        data = await self.bot.db.fetchrow(
            """
            SELECT wallet, bank, gems 
            FROM economy 
            WHERE user_id = $1
            """, 
            user_id
        )
        if not data:
            return 0, 0, 0
        return data['wallet'], data['bank'], data['gems']

    async def log_transaction(self, user_id: int, type: str, amount: int):
        """
        Log a transaction for a user.
        """
        await self.bot.db.execute(
            """
            INSERT INTO user_transactions 
            (user_id, type, amount, created_at)
            VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
            """,
            user_id, 
            type, 
            amount
        )

    @commands.command(name="start", aliases=["register"])
    @is_econ_allowed()
    async def start_economy(self, ctx: Context):
        """
        Start your economy journey with some starter coins.
        """
        exists = await self.bot.db.fetchval(
            """
            SELECT EXISTS(
                SELECT 1 
                FROM economy 
                WHERE user_id = $1
            )
            """,
            ctx.author.id
        )
        
        if exists:
            return await ctx.warn("You already have an economy account!")

        starter_coins = 1000
        starter_bank_capacity = 10000

        await self.bot.db.execute(
            """
            INSERT INTO economy (user_id, wallet, bank_capacity) 
            VALUES ($1, $2, $3)
            """,
            ctx.author.id, 
            starter_coins, 
            starter_bank_capacity
        )
        
        await self.log_transaction(ctx.author.id, "account_created", starter_coins)

        embed = Embed(
            title=f"{config.EMOJIS.ECONOMY.WELCOME} Welcome to the Economy!",
            description=(
                f"**Your account has been created with**:\n"
                f":euro: - `{starter_coins:,}` coins in your wallet\n"
                f":bank: - `{starter_bank_capacity:,}` bank capacity\n\n"
                "**Quick Start Guide:**\n"
                f"{config.EMOJIS.ECONOMY.WELCOME}- Use `;daily` for daily rewards\n"
                f"{config.EMOJIS.ECONOMY.WELCOME} - Use `;work` to earn more coins\n"
                f"{config.EMOJIS.ECONOMY.WELCOME} - Use `;bank deposit` to protect your coins\n"
            ),
        ).set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        
        await ctx.send(embed=embed)

    @commands.command(name="balance", aliases=["bal"])
    @is_econ_allowed()
    async def balance(self, ctx: Context, user: Optional[Member] = None):
        """
        Check your or another user's balance.
        """
        target = user or ctx.author
        wallet, bank, gems = await self.get_balance(target.id)

        embed = Embed(
            title=f"**{target.display_name}'s** balance",
            description=(
                f":euro:  | You have **{wallet:,}** coins in your wallet.\n"
                f":bank: |  You have **{bank:,}** coins in your bank.\n"
                f"{config.EMOJIS.ECONOMY.GEM} | You have **{gems:,}** gems."
            )
        )
        
        await ctx.send(embed=embed)

    @commands.group(name="bank", invoke_without_command=True)
    @is_econ_allowed()
    async def bank(self, ctx: Context):
        """
        Bank management commands.
        """
        wallet, bank, _ = await self.get_balance(ctx.author.id)
        bank_capacity = await self.bot.db.fetchval(
            """
            SELECT bank_capacity 
            FROM economy 
            WHERE user_id = $1
            """,
            ctx.author.id
        ) or 10000
        
        last_claim = await self.bot.db.fetchval(
            """
            SELECT last_interest 
            FROM economy 
            WHERE user_id = $1
            """,
            ctx.author.id
        )
        
        now = datetime.now()  
        
        if last_claim:
            time_diff = now - last_claim
            if time_diff.total_seconds() < 86400:
                hours_left = 24 - (time_diff.total_seconds() / 3600)
                interest_status = f"Available in {int(hours_left)} hours"
            else:
                interest_status = "Available now!"
        else:
            interest_status = "Available now!"

        embed = Embed(
            title=f"**{ctx.author.display_name}'s** Bank Account",
            description=(
                f":credit_card:  | **Balance:** {bank:,}/{bank_capacity:,}\n"
                f"💶  | Wallet: {wallet:,}\n"
                f":bar_chart:  | **Interest Status**: {interest_status}"
            )
        )
            
        await ctx.send(embed=embed)

    @bank.command(name="deposit")
    @is_econ_allowed()
    async def bank_deposit(self, ctx: Context, amount: str):
        """
        Deposit coins into your bank account.
        """
        wallet, bank, _ = await self.get_balance(ctx.author.id)
        bank_capacity = await self.bot.db.fetchval(
            """
            SELECT bank_capacity 
            FROM economy 
            WHERE user_id = $1
            """,
            ctx.author.id
        ) or 10000

        if amount.lower() == "all":
            amount = wallet
        else:
            try:
                amount = int(amount.replace(",", ""))
            except ValueError:
                return await ctx.warn("Please provide a valid number or `all`")

        if amount <= 0:
            return await ctx.warn("Amount must be positive!")
        
        if amount > wallet:
            return await ctx.warn("You don't have enough coins in your wallet!")

        space_left = bank_capacity - bank
        if amount > space_left:
            return await ctx.warn(f"Your bank only has space for {space_left:,} more coins")

        await self.bot.db.execute(
            """
            UPDATE economy 
            SET wallet = wallet - $1, bank = bank + $1 
            WHERE user_id = $2
            """,
            amount, ctx.author.id
        )
        
        await self.log_transaction(ctx.author.id, "deposit", amount)
        
        await self.eco_bank(ctx, f"Deposited **{amount:,}** coins to your bank account.")

    @bank.command(name="withdraw")
    @is_econ_allowed()
    async def bank_withdraw(self, ctx: Context, amount: str):
        """
        Withdraw coins from your bank account.
        """
        wallet, bank, _ = await self.get_balance(ctx.author.id)

        if amount.lower() == "all":
            amount = bank
        else:
            try:
                amount = int(amount.replace(",", ""))
            except ValueError:
                return await ctx.warn( "Please provide a valid number or `all`")

        if amount <= 0:
            return await ctx.warn( "Amount must be positive")
        
        if amount > bank:
            return await ctx.warn( "You don't have enough coins in your bank")

        await self.bot.db.execute(
            """
            UPDATE economy 
            SET wallet = wallet + $1, bank = bank - $1 
            WHERE user_id = $2
            """,
            amount, ctx.author.id
        )
        
        await self.log_transaction(ctx.author.id, "withdraw", amount)
        
        await self.eco_bank(ctx, f"Withdrew **{amount:,}** coinss from your bank account.")

    @bank.command(name="upgrade")
    @is_econ_allowed()
    async def bank_upgrade(self, ctx: Context):
        """
        Upgrade your bank account capacity.
        """
        wallet, _, gems = await self.get_balance(ctx.author.id)
        
        current_capacity = await self.bot.db.fetchval(
            """
            SELECT bank_capacity 
            FROM economy 
            WHERE user_id = $1
            """,
            ctx.author.id
        ) or 10000

        upgrade_cost = int(current_capacity * 0.2)
        gem_cost = max(1, int(upgrade_cost / 10000))
        new_capacity = int(current_capacity * 1.5)

        if wallet < upgrade_cost:
            return await ctx.warn( 
                f"You need {upgrade_cost:,} coins to upgrade your bank capacity!"
            )
            
        if gems < gem_cost:
            return await ctx.warn( 
                f"You need {gem_cost:,} gems to upgrade your bank capacity!"
            )

        confirm = await ctx.prompt(
            f"Upgrade your bank capacity to {new_capacity:,} coins?\n"
            f"This will cost {upgrade_cost:,} coins and {gem_cost:,} gems!"
        )
        
        if not confirm:
            return await ctx.warn("Upgrade cancelled!")

        await self.bot.db.execute(
            """
            UPDATE economy 
            SET wallet = wallet - $1, gems = gems - $2, bank_capacity = $3 
            WHERE user_id = $4
            """,
            upgrade_cost, gem_cost, new_capacity, ctx.author.id
        )
        
        await self.eco_bank(
            ctx, f"Upgraded your bank capacity to {new_capacity:,} coins!"
        )

    @bank.command(name="interest", aliases=["claim"])
    @is_econ_allowed()
    async def bank_interest(self, ctx: Context):
        """
        Claim your daily bank interest.
        """
        _, bank, _ = await self.get_balance(ctx.author.id)
        
        last_claim = await self.bot.db.fetchval(
            """
            SELECT last_interest 
            FROM economy 
            WHERE user_id = $1
            """,
            ctx.author.id
        )
        
        now = datetime.now() 
        
        if last_claim:
            time_diff = now - last_claim
            if time_diff.total_seconds() < 86400:
                hours_left = 24 - (time_diff.total_seconds() / 3600)
                return await ctx.warn( 
                    f"You can claim interest again in {int(hours_left)} hours"
                )

        if bank <= 0:
            return await ctx.warn("You need to have coins in your bank to earn interest!")

        interest_rate = 0.01
        interest = int(bank * interest_rate)
        if interest < 1:
            interest = 1

        await self.bot.db.execute(
            """
            UPDATE economy 
            SET bank = bank + $1, last_interest = $2 
            WHERE user_id = $3
            """,
            interest, now, ctx.author.id
        )
        
        await self.eco_bank(ctx, f"You earned {interest:,} coins in interest!")

    @commands.command(name="transfer", aliases=["pay", "give"])
    @is_econ_allowed()
    async def transfer(self, ctx: Context, user: Member, amount: str):
        """
        Transfer coins to another user.
        """
        if user.bot:
            return await ctx.warn("You can't transfer coins to bots!")
            
        if user.id == ctx.author.id:
            return await ctx.warn("You can't transfer coins to yourself!")

        wallet, _, _ = await self.get_balance(ctx.author.id)

        try:
            amount = int(amount.replace(",", ""))
        except ValueError:
            return await ctx.warn("Please provide a valid number!")

        if amount <= 0:
            return await ctx.warn("Amount must be positive!")
        
        if amount > wallet:
            return await ctx.warn("You don't have enough coins in your wallet!")

        confirm = await ctx.prompt(
            f"Are you sure you want to transfer {amount:,} coins to {user.name}?"
        )
        
        if not confirm:
            return await ctx.warn("Transfer cancelled!")

        async with self.bot.db.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    UPDATE economy 
                    SET wallet = wallet - $1 
                    WHERE user_id = $2
                    """,
                    amount, 
                    ctx.author.id
                )
                await conn.execute(
                    """
                    INSERT INTO economy (user_id, wallet) 
                    VALUES ($1, $2) 
                    ON CONFLICT (user_id) 
                    DO UPDATE SET wallet = economy.wallet + $2
                    """,
                    user.id, 
                    amount
                )
        
        await self.log_transaction(ctx.author.id, "transfer_sent", -amount)
        await self.log_transaction(user.id, "transfer_received", amount)
        
        await ctx.approve(f"Transferred {amount:,} coins to {user.name}")

    @commands.command(name="daily")
    @is_econ_allowed()
    async def daily_reward(self, ctx: Context):
        """
        Claim your daily reward.
        """
        last_daily = await self.bot.db.fetchval(
            """
            SELECT last_daily 
            FROM economy 
            WHERE user_id = $1
            """,
            ctx.author.id
        )
        
        current_streak = await self.bot.db.fetchval(
            """
            SELECT daily_streak 
            FROM economy 
            WHERE user_id = $1
            """,
            ctx.author.id
        ) or 0

        now = datetime.now()
        
        if last_daily:
            time_diff = now - last_daily
            if time_diff.total_seconds() < 86400:  
                hours_left = 24 - (time_diff.total_seconds() / 3600)
                return await ctx.warn( 
                    f"You can claim your daily reward again in {int(hours_left)} hours"
                )
            
            if time_diff.total_seconds() >= 172800:  
                current_streak = 0
        
        base_coins = 1000
        streak_bonus = min(current_streak * 100, 1000) 
        total_coins = base_coins + streak_bonus
        
        gems = 0
        if (current_streak + 1) % 7 == 0:
            gems = (current_streak + 1) // 7  
        
        await self.bot.db.execute(
            """
            INSERT INTO economy (user_id, wallet, gems, last_daily, daily_streak) 
            VALUES ($1, $2, $3, $4, $5) 
            ON CONFLICT (user_id) DO UPDATE SET 
                wallet = economy.wallet + $2,
                gems = economy.gems + $3,
                last_daily = $4,
                daily_streak = $5
                """,
            ctx.author.id, 
            total_coins, 
            gems, 
            now, 
            current_streak + 1
        )
        
        await self.log_transaction(ctx.author.id, "daily", total_coins)
        
        next_milestone = 7 - ((current_streak + 1) % 7)
        embed = Embed(
            title="Daily Reward Claimed!",
            description= (
                ":moneybag:  |  Streak Bonus\n"
                ":euro:  |  Reward\n"
                "+---- Total\n"
                f"{total_coins:,}\n\n"
                ":fire: | Streak\n"
                f"{current_streak+1} days\n\n"
                ":rock: | Next Milestone\n"
                f"{next_milestone} days until gem reward!"
                ),
            color=config.COLORS.NEUTRAL
        ).set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.group(name="work", invoke_without_command=True)
    @is_econ_allowed()
    async def work(self, ctx: Context):
        """
        Work to earn money.
        """
        job_data = await self.bot.db.fetchrow(
            """
            SELECT current_job, job_level, last_work, employer_id 
            FROM jobs WHERE user_id = $1
            """, 
            ctx.author.id
        )
        
        if not job_data or not job_data['current_job']:
            return await ctx.warn( 
                "You don't have a job! Use `jobs` to see available positions"
            )

        now = datetime.now()
        
        if job_data['last_work']:
            time_diff = now - job_data['last_work']
            if time_diff.total_seconds() < 3600:  
                minutes_left = 60 - (time_diff.total_seconds() / 60)
                return await ctx.warn( 
                    f"You can work again in {int(minutes_left)} minutes"
                )

        base_pay = 500
        level_bonus = (job_data['job_level'] - 1) * 50
        
        if job_data['employer_id']:  
            contract = await self.bot.db.fetchrow(
                """
                SELECT business_id, salary 
                FROM contracts 
                WHERE employee_id = $1
                """,
                ctx.author.id
            )
            if contract:
                base_pay = contract['salary']

        total_pay = base_pay + level_bonus

        if job_data['employer_id']: 
            business_balance = await self.bot.db.fetchval(
                """
                SELECT balance 
                FROM businesses 
                WHERE owner_id = $1
                """,
                job_data['employer_id']
            )
            
            if business_balance < total_pay:
                return await ctx.warn( 
                    "Your employer's business doesn't have enough funds to pay you!"
                )

        async with self.bot.db.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    UPDATE jobs 
                    SET job_experience = job_experience + 1,
                    last_work = $2
                    WHERE user_id = $1
                    """,
                    ctx.author.id, now
                )

                if job_data['employer_id']:
                    await conn.execute(
                        """
                        UPDATE businesses 
                        SET balance = balance - $1 
                        WHERE owner_id = $2
                        """,
                        total_pay, job_data['employer_id']
                    )
                    
                    await conn.execute(
                        """
                        INSERT INTO business_stats (business_id, total_expenses)
                        VALUES ($1, $2)
                        ON CONFLICT (business_id) 
                        DO UPDATE SET total_expenses = business_stats.total_expenses + $2
                        """,
                        contract['business_id'], total_pay
                    )
                    
                    await conn.execute(
                        """
                        INSERT INTO employee_stats (business_id, employee_id, work_count, total_earned)
                        VALUES ($1, $2, 1, $3)
                        ON CONFLICT (business_id, employee_id) 
                        DO UPDATE SET 
                            work_count = employee_stats.work_count + 1,
                            total_earned = employee_stats.total_earned + $3
                            """,
                        contract['business_id'], ctx.author.id, total_pay
                    )

                await conn.execute(
                    """
                    UPDATE economy 
                    SET wallet = wallet + $1 
                    WHERE user_id = $2
                    """,
                    total_pay, ctx.author.id
                )

        exp = await self.bot.db.fetchval(
            """
            SELECT job_experience 
            FROM jobs 
            WHERE user_id = $1
            """,
            ctx.author.id
        )
        
        if exp >= job_data['job_level'] * 10: 
            await self.bot.db.execute(
                """
                UPDATE jobs 
                SET job_level = job_level + 1,
                job_experience = 0
                WHERE user_id = $1
                """,
                ctx.author.id
            )
            await ctx.send(f"{config.EMOJIS.ECONOMY.WELCOME} You've been promoted to level {job_data['job_level'] + 1}!")

        await self.log_transaction(ctx.author.id, "work", total_pay)
        
        await ctx.approve(f"You earned {total_pay:,} coins from working!")

    @commands.group(name="business", invoke_without_command=True)
    @is_econ_allowed()
    async def business(self, ctx: Context):
        """
        Business management commands.
        """
        business = await self.bot.db.fetchrow(
            """
            SELECT * FROM businesses 
            WHERE owner_id = $1
            """,
            ctx.author.id
        )
        
        if not business:
            return await ctx.warn( 
                "You don't own a business! Use `business create` to start one"
            )

        employees = await self.bot.db.fetch(
            """
            SELECT employee_id, salary, position 
            FROM contracts WHERE business_id = $1
            """,
            business['business_id']
        )

        embed = Embed(
            title=f"{business['name']}",
            color=config.COLORS.NEUTRAL
        )
        embed.add_field(
            name="Balance",
            value=f":euro: {business['balance']:,} coins",
            inline=False
        )
        embed.add_field(
            name="Employees",
            value=f"{len(employees)}/{business['employee_limit']}",
            inline=False
        )
        
        if employees:
            employee_list = []
            for emp in employees:
                user = ctx.guild.get_member(emp['employee_id'])
                if user:
                    employee_list.append(
                        f"{user.name} - {emp['position']} ({emp['salary']:,} coins/hr)"
                    )
            embed.add_field(
                name="Employee List",
                value="\n".join(employee_list) or "No employees",
                inline=False
            )

        await ctx.send(embed=embed)

    @commands.command(name="quit", aliases=["resign"])
    @is_econ_allowed()
    async def quit_job(self, ctx: Context):
        """
        Quit your current job.
        """
        contract = await self.bot.db.fetchrow(
            """
            SELECT c.*, b.name as business_name 
            FROM contracts c 
            JOIN businesses b ON b.business_id = c.business_id 
            WHERE c.employee_id = $1
            """,
            ctx.author.id
        )

        if not contract:
            return await ctx.warn("You don't have a job!")

        confirm = await ctx.prompt(
            f"Are you sure you want to quit your job at {contract['business_name']}? "
            "You will lose your position and salary."
        )

        if not confirm:
            return await ctx.warn("Resignation cancelled")

        async with self.bot.db.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    DELETE FROM contracts 
                    WHERE employee_id = $1
                    """,
                    ctx.author.id
                )
                
                await conn.execute(
                    """
                    UPDATE jobs 
                    SET current_job = NULL, employer_id = NULL 
                    WHERE user_id = $1
                    """,
                    ctx.author.id
                )

        await ctx.approve(f"You have quit your job at {contract['business_name']}!")

        owner = ctx.guild.get_member(contract["owner_id"])
        if owner:
            try:
                await owner.send(
                    f"📢 {ctx.author.name} has quit their position as "
                    f"{contract['position']} at {contract['business_name']}."
                )
            except:
                pass

    @business.command(name="create")
    @is_econ_allowed()
    async def business_create(self, ctx: Context, *, name: str):
        """
        Create a new business.
        """
        if len(name) > 32:
            return await ctx.warn("Business name must be 32 characters or less")

        existing = await self.bot.db.fetchrow(
            """
            SELECT * FROM businesses 
            WHERE owner_id = $1
            """,
            ctx.author.id
        )
        
        if existing:
            return await ctx.warn("You already own a business!")

        cost = 100000
        wallet, _, _ = await self.get_balance(ctx.author.id)
        
        if wallet < cost:
            return await ctx.warn( 
                f"You need {cost:,} coins to create a business"
            )

        confirm = await ctx.prompt(
            f"Create business \"{name}\" for {cost:,} coins?"
        )
        
        if not confirm:
            return await ctx.warn( "Business creation cancelled")

        try:
            await self.bot.db.execute(
                """
                INSERT INTO businesses 
                (name, owner_id) 
                VALUES ($1, $2)
                """,
                name, ctx.author.id
            )
            await self.bot.db.execute(
                """
                UPDATE economy 
                SET wallet = wallet - $1 
                WHERE user_id = $2
                """,
                cost, ctx.author.id
            )
        except Exception as e:
            if 'unique constraint' in str(e).lower():
                return await ctx.warn("A business with that name already exists!")
            raise

        await ctx.approve(f"Created business \"{name}\"!")

    @business.command(name="hire")
    @is_econ_allowed()
    async def business_hire(self, ctx: Context, user: Member, salary: int, *, position: str):
        """
        Hire an employee for your business.
        """
        if user.bot:
            return await ctx.warn( "You can't hire bots!")

        if user.id == ctx.author.id:
            return await ctx.warn( "You can't hire yourself!")

        business = await self.bot.db.fetchrow(
            """
            SELECT * FROM businesses 
            WHERE owner_id = $1
            """,
            ctx.author.id
        )
        
        if not business:
            return await ctx.warn("You don't own a business!")

        if salary < 100:
            return await ctx.warn("Minimum salary is 100 coins per hour")

        employee_count = await self.bot.db.fetchval(
            """
            SELECT COUNT(*) 
            FROM contracts 
            WHERE business_id = $1
            """,
            business["business_id"]
        )
        
        if employee_count >= business["employee_limit"]:
            return await ctx.warn("Your business has reached its employee limit!")

        confirm = await ctx.prompt(
            f"Hire {user.name} as {position} for {salary:,} coins per hour?"
        )
        
        if not confirm:
            return await ctx.warn( "Hiring cancelled")

        try:
            await self.bot.db.execute(
                """
                INSERT INTO contracts 
                (business_id, employee_id, salary, position) 
                VALUES 
                ($1, $2, $3, $4)
                """,
                business["business_id"], 
                user.id, 
                salary, 
                position
            )
            await self.bot.db.execute(
                """
                INSERT INTO jobs 
                (user_id, current_job, employer_id) 
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id) 
                DO UPDATE 
                SET current_job = $2, 
                employer_id = $3
                """,
                user.id, 
                position, 
                ctx.author.id
            )
        except Exception as e:
            if "unique constraint" in str(e).lower():
                return await ctx.warn( f"{user.name} already has a job!")
            raise

        await ctx.approve(f"Hired {user.name} as {position}!")

    @business.command(name="fire")
    @is_econ_allowed()
    async def business_fire(self, ctx: Context, user: Member):
        """
        Fire an employee from your business.
        """
        business = await self.bot.db.fetchrow(
            """
            SELECT * FROM businesses 
            WHERE owner_id = $1
            """,
            ctx.author.id
        )
        
        if not business:
            return await ctx.warn("You don't own a business!")

        contract = await self.bot.db.fetchrow(
            """
            SELECT * FROM contracts 
            WHERE business_id = $1 
            AND employee_id = $2
            """,
            business["business_id"], 
            user.id
        )
        
        if not contract:
            return await ctx.warn(f"{user.name} doesn't work for your business!")

        confirm = await ctx.prompt(
            f"Are you sure you want to fire {user.name}?"
        )
        
        if not confirm:
            return await ctx.warn("Firing cancelled")

        await self.bot.db.execute(
            """
            DELETE FROM contracts 
            WHERE business_id = $1 
            AND employee_id = $2
            """,
            business["business_id"], 
            user.id
        )
        
        await self.bot.db.execute(
            """
            UPDATE jobs 
            SET current_job = NULL, 
            employer_id = NULL 
            WHERE user_id = $1
            """,
            user.id
        )
        
        await ctx.approve(f"Fired {user.name}!")

    @business.command(name="promote")
    @is_econ_allowed()
    async def business_promote(self, ctx: Context, user: Member, new_salary: int, *, new_position: str):
        """
        Promote an employee to a new position with new salary.
        """
        business = await self.bot.db.fetchrow(
            """
            SELECT * FROM businesses 
            WHERE owner_id = $1
            """,
            ctx.author.id
        )
        
        if not business:
            return await ctx.warn("You don't own a business!")

        contract = await self.bot.db.fetchrow(
            """
            SELECT * FROM contracts 
            WHERE business_id = $1 
            AND employee_id = $2
            """,
            business["business_id"], 
            user.id
        )
        
        if not contract:
            return await ctx.warn(f"{user.name} doesn't work for your business!")

        if new_salary < 100:
            return await ctx.warn("Minimum salary is 100 coins per hour")

        confirm = await ctx.prompt(
            f"Promote {user.name} to {new_position} with {new_salary:,} coins per hour salary?"
        )
        
        if not confirm:
            return await ctx.warn("Promotion cancelled")

        await self.bot.db.execute(
            """
            UPDATE contracts 
            SET position = $1, 
            salary = $2 
            WHERE business_id = $3 
            AND employee_id = $4
            """,
            new_position, 
            new_salary, 
            business["business_id"], 
            user.id
        )
        
        await self.bot.db.execute(
            """
            UPDATE jobs 
            SET current_job = $1 
            WHERE user_id = $2
            """,
            new_position, 
            user.id
        )
        
        await ctx.approve(f"Promoted {user.name} to {new_position}!")

    @business.command(name="deposit")
    @is_econ_allowed()
    async def business_deposit(self, ctx: Context, amount: str):
        """
        Deposit coins into your business account.
        """
        business = await self.bot.db.fetchrow(
            """
            SELECT * FROM businesses 
            WHERE owner_id = $1
            """,
            ctx.author.id
        )
        
        if not business:
            return await ctx.warn("You don't own a business!")

        wallet, _, _ = await self.get_balance(ctx.author.id)

        if amount.lower() == "all":
            amount = wallet
        else:
            try:
                amount = int(amount.replace(",", ""))
            except ValueError:
                return await ctx.warn("Please provide a valid number or 'all'")

        if amount <= 0:
            return await ctx.warn("Amount must be positive")
        
        if amount > wallet:
            return await ctx.warn("You don't have enough coins in your wallet")

        confirm = await ctx.prompt(
            f"Deposit {amount:,} coins into your business account?"
        )
        
        if not confirm:
            return await ctx.warn( "Deposit cancelled")

        await self.bot.db.execute(
            """
            UPDATE businesses 
            SET balance = balance + $1 
            WHERE business_id = $2
            """,
            amount, 
            business["business_id"]
        )
        
        await self.bot.db.execute(
            """UPDATE economy 
            SET wallet = wallet - $1 
            WHERE user_id = $2""",
            amount, ctx.author.id
        )
        
        await ctx.approve(f"Deposited {amount:,} coins into your business!")

    @business.command(name="withdraw")
    @is_econ_allowed()
    async def business_withdraw(self, ctx: Context, amount: str):
        """Withdraw coins from your business account"""
        business = await self.bot.db.fetchrow(
            """SELECT * FROM businesses WHERE owner_id = $1""",
            ctx.author.id
        )
        
        if not business:
            return await ctx.warn( "You don't own a business!")

        if amount.lower() == "all":
            amount = business["balance"]
        else:
            try:
                amount = int(amount.replace(",", ""))
            except ValueError:
                return await ctx.warn( "Please provide a valid number or 'all'")

        if amount <= 0:
            return await ctx.warn( "Amount must be positive")
        
        if amount > business["balance"]:
            return await ctx.warn( "Your business doesn't have enough coins")

        confirm = await ctx.prompt(
            f"Withdraw {amount:,} coins from your business account?"
        )
        
        if not confirm:
            return await ctx.warn( "Withdrawal cancelled")

        await self.bot.db.execute(
            """UPDATE businesses 
            SET balance = balance - $1 
            WHERE business_id = $2""",
            amount, business["business_id"]
        )
        
        await self.bot.db.execute(
            """UPDATE economy 
            SET wallet = wallet + $1 
            WHERE user_id = $2""",
            amount, ctx.author.id
        )
        
        await ctx.approve(f"Withdrew {amount:,} coins from your business!")

    @business.command(name="upgrade")
    @is_econ_allowed()
    async def business_upgrade(self, ctx: Context):
        """Upgrade your business employee limit"""
        business = await self.bot.db.fetchrow(
            """SELECT * FROM businesses WHERE owner_id = $1""",
            ctx.author.id
        )
        
        if not business:
            return await ctx.warn( "You don't own a business!")

        upgrade_cost = business["employee_limit"] * 50000
        new_limit = business["employee_limit"] + 5

        if business["balance"] < upgrade_cost:
            return await ctx.warn( 
                f"Your business needs {upgrade_cost:,} coins to upgrade employee limit"
            )

        confirm = await ctx.prompt(
            f"Upgrade employee limit to {new_limit} for {upgrade_cost:,} coins?"
        )
        
        if not confirm:
            return await ctx.warn( "Upgrade cancelled")

        await self.bot.db.execute(
            """UPDATE businesses 
            SET balance = balance - $1, employee_limit = $2 
            WHERE business_id = $3""",
            upgrade_cost, new_limit, business["business_id"]
        )
        
        await ctx.approve(
            f"Upgraded employee limit to {new_limit}!"
        )

    @business.command(name="stats")
    @is_econ_allowed()
    async def business_stats(self, ctx: Context):
        """View business statistics"""
        business = await self.bot.db.fetchrow(
            """SELECT * FROM businesses WHERE owner_id = $1""",
            ctx.author.id
        )
        
        if not business:
            return await ctx.warn( "You don't own a business!")

        stats = await self.bot.db.fetchrow(
            """SELECT total_revenue, total_expenses 
            FROM business_stats WHERE business_id = $1""",
            business["business_id"]
        )
        
        if not stats:
            stats = {"total_revenue": 0, "total_expenses": 0}

        employees = await self.bot.db.fetch(
            """SELECT employee_id, position, salary 
            FROM contracts WHERE business_id = $1""",
            business["business_id"]
        )

        embed = Embed(
            title=f"📊 {business['name']} Statistics",
            color=config.COLORS.NEUTRAL
        )
        
        revenue = stats["total_revenue"]
        expenses = stats["total_expenses"]
        profit = revenue - expenses
        
        embed.add_field(
            name="💰 Revenue",
            value=f"{revenue:,} coins",
            inline=True
        )
        embed.add_field(
            name="💸 Expenses",
            value=f"{expenses:,} coins",
            inline=True
        )
        embed.add_field(
            name="📈 Profit",
            value=f"{profit:,} coins",
            inline=True
        )
        
        employee_list = []
        for emp in employees:
            user = ctx.guild.get_member(emp["employee_id"])
            if user:
                employee_list.append(
                    f"{user.name} - {emp['position']} ({emp['salary']:,}/hr)"
                )

        if employee_list:
            embed.add_field(
                name=f"👥 Employees ({len(employee_list)})",
                value="\n".join(employee_list),
                inline=False
            )

        await ctx.send(embed=embed)

    @business.command(name="performance")
    @is_econ_allowed()
    async def business_performance(self, ctx: Context, employee: Member):
        """View an employee's performance"""
        business = await self.bot.db.fetchrow(
            """SELECT * FROM businesses WHERE owner_id = $1""",
            ctx.author.id
        )
        
        if not business:
            return await ctx.warn( "You don't own a business!")

        contract = await self.bot.db.fetchrow(
            """SELECT * FROM contracts 
            WHERE business_id = $1 AND employee_id = $2""",
            business["business_id"], employee.id
        )
        
        if not contract:
            return await ctx.warn( f"{employee.name} doesn't work for your business!")

        stats = await self.bot.db.fetchrow(
            """SELECT work_count, total_earned 
            FROM employee_stats 
            WHERE business_id = $1 AND employee_id = $2""",
            business["business_id"], employee.id
        )
        
        if not stats:
            stats = {"work_count": 0, "total_earned": 0}

        embed = Embed(
            title=f"{employee.name}'s Employee Performance",
            color=config.COLORS.NEUTRAL
        )
        
        embed.add_field(
            name="Position",
            value=contract["position"],
            inline=True
        )
        embed.add_field(
            name="Salary",
            value=f"{contract['salary']:,}/hr",
            inline=True
        )
        embed.add_field(
            name="Work Count",
            value=f"{stats['work_count']:,}",
            inline=False
        )
        embed.add_field(
            name="Total Earned",
            value=f"{stats['total_earned']:,} coins",
            inline=True
        )

        await ctx.send(embed=embed)

    @business.command(name="top")
    @is_econ_allowed()
    async def business_top(self, ctx: Context):
        """View the top businesses"""
        businesses = await self.bot.db.fetch(
            """
            SELECT name, owner_id, balance 
            FROM businesses 
            ORDER BY balance DESC LIMIT 10
            """
        )

        if not businesses:
            return await ctx.warn( "No businesses found!")

        embed = Embed(
            title=" Top Businesses",
            color=discord.Color.gold()
        )

        for i, business in enumerate(businesses, 1):
            owner = ctx.guild.get_member(business["owner_id"])
            if owner:
                embed.add_field(
                    name=f"#{i} {business['name']}",
                    value=f"{config.EMOJIS.ECONOMY.CROWN} Owner: {owner.name}\n:euro: Balance: {business['balance']:,} coins",
                    inline=False
                )

        await ctx.send(embed=embed)

    @business.command(name="rename")
    @is_econ_allowed()
    async def business_rename(self, ctx: Context, *, new_name: str):
        """Rename your business (costs coins)"""
        if len(new_name) > 32:
            return await ctx.warn("Business name must be 32 characters or less!")

        business = await self.bot.db.fetchrow(
            """
            SELECT * FROM businesses 
            WHERE owner_id = $1
            """,
            ctx.author.id
        )
        
        if not business:
            return await ctx.warn( "You don't own a business!")

        cost = 25000
        if business["balance"] < cost:
            return await ctx.warn( f"Your business needs {cost:,} coins to rename")

        confirm = await ctx.prompt(
            f"Rename your business to {new_name} for {cost:,} coins?"
        )
        
        if not confirm:
            return await ctx.warn( "Rename cancelled")

        try:
            await self.bot.db.execute(
                """UPDATE businesses 
                SET name = $1, balance = balance - $2 
                WHERE business_id = $3""",
                new_name, cost, business["business_id"]
            )
        except Exception as e:
            if "unique constraint" in str(e).lower():
                return await ctx.warn( "A business with that name already exists!")
            raise

        await ctx.approve(f"Renamed business to {new_name}!")

    @business.command(name="description", aliases=["desc"])
    @is_econ_allowed()
    async def business_description(self, ctx: Context, *, description: str):
        """Set your business description"""
        if len(description) > 1024:
            return await ctx.warn( "Description must be 1024 characters or less")

        business = await self.bot.db.fetchrow(
            """SELECT * FROM businesses WHERE owner_id = $1""",
            ctx.author.id
        )
        
        if not business:
            return await ctx.warn( "You don't own a business!")

        await self.bot.db.execute(
            """UPDATE businesses 
            SET description = $1 
            WHERE business_id = $2""",
            description, business["business_id"]
        )
        
        await ctx.approve("Updated business description!")

    @business.command(name="info")
    @is_econ_allowed()
    async def business_info(self, ctx: Context, *, business_name: str = None):
        """View detailed information about a business"""
        if business_name:
            business = await self.bot.db.fetchrow(
                """SELECT * FROM businesses WHERE name = $1""",
                business_name
            )
            if not business:
                return await ctx.warn( "Business not found!")
        else:
            business = await self.bot.db.fetchrow(
                """SELECT * FROM businesses WHERE owner_id = $1""",
                ctx.author.id
            )
            if not business:
                return await ctx.warn( "You don't own a business!")

        owner = ctx.guild.get_member(business["owner_id"])
        employee_count = await self.bot.db.fetchval(
            """SELECT COUNT(*) FROM contracts WHERE business_id = $1""",
            business["business_id"]
        )

        embed = Embed(
            title=f"🏢 {business['name']}",
            description=business.get("description", "No description set"),
            color=config.COLORS.NEUTRAL
        )
        
        embed.add_field(
            name="Owner",
            value=owner.mention if owner else "Unknown",
            inline=True
        )
        embed.add_field(
            name="Founded",
            value=business["created_at"].strftime("%Y-%m-%d"),
            inline=True
        )
        embed.add_field(
            name="Employees",
            value=f"👥 {employee_count}/{business['employee_limit']}",
            inline=True
        )
        embed.add_field(
            name="Balance",
            value=f"{business['balance']:,} coins",
            inline=True
        )

        await ctx.send(embed=embed)

    @business.command(name="payroll")
    @is_econ_allowed()
    async def business_payroll(self, ctx: Context):
        """View your business's payroll information"""
        business = await self.bot.db.fetchrow(
            """SELECT * FROM businesses WHERE owner_id = $1""",
            ctx.author.id
        )
        
        if not business:
            return await ctx.warn( "You don't own a business!")

        employees = await self.bot.db.fetch(
            """SELECT employee_id, salary, position 
            FROM contracts WHERE business_id = $1""",
            business["business_id"]
        )

        if not employees:
            return await ctx.warn( "Your business has no employees!")

        total_hourly = sum(emp["salary"] for emp in employees)
        daily_cost = total_hourly * 24
        weekly_cost = daily_cost * 7

        embed = Embed(
            title=f"💰 {business['name']} Payroll",
            color=config.COLORS.NEUTRAL
        )
        
        embed.add_field(
            name="Hourly Cost",
            value=f"{total_hourly:,} coins",
            inline=True
        )
        embed.add_field(
            name="Daily Cost",
            value=f"{daily_cost:,} coins",
            inline=True
        )
        embed.add_field(
            name="Weekly Cost",
            value=f"{weekly_cost:,} coins",
            inline=True
        )
        
        employee_list = []
        for emp in employees:
            user = ctx.guild.get_member(emp["employee_id"])
            if user:
                employee_list.append(
                    f"{user.name} - {emp['position']}: {emp['salary']:,}/hr"
                )

        if employee_list:
            embed.add_field(
                name="Employee Salaries",
                value="\n".join(employee_list),
                inline=False
            )

        await ctx.send(embed=embed)

    @commands.group(name="jobs", invoke_without_command=True)
    @is_econ_allowed()
    async def jobs(self, ctx: Context):
        """
        View available job listings.
        """
        listings = await self.bot.db.fetch(
            """SELECT bj.job_id, bj.position, bj.salary, bj.description, 
                    b.name as business_name, b.owner_id 
            FROM business_jobs bj 
            JOIN businesses b ON b.business_id = bj.business_id 
            ORDER BY bj.job_id DESC
            LIMIT 10"""
        )

        if not listings:
            return await ctx.warn( "No job listings available!")

        embed = Embed(
            title="Available Jobs",
            color=config.COLORS.NEUTRAL
        )

        for job in listings:
            owner = ctx.guild.get_member(job["owner_id"])
            description = job["description"] or "No description provided"
            if owner:
                embed.add_field(
                    name=f"{job['business_name']} - {job['position']}",
                    value=(
                        f":euro: Salary: {job['salary']:,}/hr\n"
                        f"📝 Description: {description}\n"
                        f"{config.EMOJIS.ECONOMY.CROWN} Owner: {owner.name}\n"
                        f"-# **Use ;jobs apply 1 to apply**"
                    ),
                    inline=False
                )
        
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar)

        await ctx.send(embed=embed)

    @jobs.command(name="apply")
    @is_econ_allowed()
    async def jobs_apply(self, ctx: Context, job_id: int):
        """
        Apply for a job listing.
        """
        job = await self.bot.db.fetchrow(
            """SELECT bj.*, b.owner_id, b.name as business_name 
            FROM business_jobs bj 
            JOIN businesses b ON b.business_id = bj.business_id 
            WHERE bj.job_id = $1""",
            job_id
        )

        if not job:
            return await ctx.warn( "Job listing not found!")

        existing_job = await self.bot.db.fetchrow(
            """SELECT * FROM jobs WHERE user_id = $1""",
            ctx.author.id
        )
        
        if existing_job and existing_job["current_job"]:
            return await ctx.warn( "You already have a job!")

        owner = ctx.guild.get_member(job["owner_id"])
        if not owner:
            return await ctx.warn( "Business owner not found!")

        await ctx.send(
            f"{owner.mention}, {ctx.author.name} has applied for the "
            f"{job['position']} position at {job['business_name']}!"
        )
        
        await ctx.approve(
            f"Applied for {job['position']} at {job['business_name']}!"
        )

    @business.group(name="hiring", invoke_without_command=True)
    @is_econ_allowed()
    async def business_hiring(self, ctx: Context):
        """Manage your business job listings"""
        business = await self.bot.db.fetchrow(
            """SELECT * FROM businesses WHERE owner_id = $1""",
            ctx.author.id
        )
        
        if not business:
            return await ctx.warn( "You don't own a business!")

        listings = await self.bot.db.fetch(
            """SELECT * FROM business_jobs WHERE business_id = $1""",
            business["business_id"]
        )

        if not listings:
            return await ctx.warn( 
                "No active job listings! Use `business hiring post` to create one"
            )

        embed = Embed(
            title=f"{business['name']} Job Listings",
            color=config.COLORS.NEUTRAL
        )

        for job in listings:
            embed.add_field(
                name=f"ID: {job['job_id']} - {job['position']}",
                value=(
                    f":euro: Salary: {job['salary']:,}/hr\n"
                    f"📝 Description: {job['description']}"
                ),
                inline=False
            )
        
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)
        await ctx.send(embed=embed)

    @business_hiring.command(name="post")
    @is_econ_allowed()
    async def business_hiring_post(
        self, ctx: Context, salary: int, position: str, *, description: str
    ):
        """Post a new job listing"""
        business = await self.bot.db.fetchrow(
            """SELECT * FROM businesses WHERE owner_id = $1""",
            ctx.author.id
        )
        
        if not business:
            return await ctx.warn( "You don't own a business!")

        if salary < 100:
            return await ctx.warn( "Minimum salary is 100 coins per hour")

        if len(description) > 1024:
            return await ctx.warn( "Description must be 1024 characters or less")

        await self.bot.db.execute(
            """INSERT INTO business_jobs (
                business_id, position, salary, description
            ) VALUES ($1, $2, $3, $4)""",
            business["business_id"], position, salary, description
        )
        
        await ctx.approve("Posted job listing!")

    @business_hiring.command(name="remove")
    @is_econ_allowed()
    async def business_hiring_remove(self, ctx: Context, job_id: int):
        """Remove a job listing"""
        business = await self.bot.db.fetchrow(
            """SELECT * FROM businesses WHERE owner_id = $1""",
            ctx.author.id
        )
        
        if not business:
            return await ctx.warn( "You don't own a business!")

        job = await self.bot.db.fetchrow(
            """SELECT * FROM business_jobs 
            WHERE job_id = $1 AND business_id = $2""",
            job_id, business["business_id"]
        )
        
        if not job:
            return await ctx.warn( "Job listing not found!")

        await self.bot.db.execute(
            """DELETE FROM business_jobs WHERE job_id = $1""",
            job_id
        )
        
        await ctx.approve("Removed job listing!")

    @business.command(name="managers")
    @is_econ_allowed()
    async def business_managers(self, ctx: Context, user: Member):
        """Give an employee hiring permissions"""
        business = await self.bot.db.fetchrow(
            """SELECT * FROM businesses WHERE owner_id = $1""",
            ctx.author.id
        )
        
        if not business:
            return await ctx.warn( "You don't own a business!")

        contract = await self.bot.db.fetchrow(
            """SELECT * FROM contracts 
            WHERE business_id = $1 AND employee_id = $2""",
            business["business_id"], user.id
        )
        
        if not contract:
            return await ctx.warn( f"{user.name} doesn't work for your business!")

        current_status = contract["can_hire"]
        new_status = not current_status

        await self.bot.db.execute(
            """UPDATE contracts 
            SET can_hire = $1 
            WHERE business_id = $2 AND employee_id = $3""",
            new_status, business["business_id"], user.id
        )
        
        status_text = "can now" if new_status else "can no longer"
        await ctx.approve(
            f"{user.name} {status_text} hire employees!"
        )

    @business_hiring.command(name="applications", aliases=["apps"])
    @is_econ_allowed()
    async def business_applications(self, ctx: Context):
        """View pending job applications"""
        business = await self.bot.db.fetchrow(
            """SELECT * FROM businesses WHERE owner_id = $1""",
            ctx.author.id
        )
        
        if not business:
            return await ctx.warn( "You don't own a business!")

        can_review = False
        if ctx.author.id == business["owner_id"]:
            can_review = True
        else:
            contract = await self.bot.db.fetchrow(
                """SELECT can_hire FROM contracts 
                WHERE business_id = $1 AND employee_id = $2""",
                business["business_id"], ctx.author.id
            )
            if contract and contract["can_hire"]:
                can_review = True

        if not can_review:
            return await ctx.warn( "You don't have permission to view applications!")

        applications = await self.bot.db.fetch(
            """SELECT ja.*, bj.position, bj.salary
            FROM job_applications ja
            JOIN business_jobs bj ON ja.job_id = bj.job_id
            WHERE bj.business_id = $1 AND ja.status = 'pending'
            ORDER BY ja.applied_at DESC""",
            business["business_id"]
        )

        if not applications:
            return await ctx.warn( "No pending applications!")

        embed = Embed(
            title=f"📝 Pending Applications - {business['name']}",
            color=config.COLORS.NEUTRAL
        )

        for app in applications:
            applicant = ctx.guild.get_member(app["applicant_id"])
            if applicant:
                embed.add_field(
                    name=f"Application #{app['application_id']}",
                    value=(
                        f"👤 Applicant: {applicant.name}\n"
                        f"💼 Position: {app['position']}\n"
                        f":euro: Salary: {app['salary']:,}/hr\n"
                        f"📅 Applied: {app['applied_at'].strftime('%Y-%m-%d %H:%M')}\n"
                        f"Use `business hiring approve/deny {app['application_id']}`"
                    ),
                    inline=False
                )

        await ctx.send(embed=embed)

    @business_hiring.command(name="approve")
    @is_econ_allowed()
    async def business_approve_application(self, ctx: Context, application_id: int):
        """Approve a job application"""
        business = await self.bot.db.fetchrow(
            """SELECT * FROM businesses WHERE owner_id = $1""",
            ctx.author.id
        )
        
        if not business:
            return await ctx.warn( "You don't own a business!")

        can_approve = False
        if ctx.author.id == business["owner_id"]:
            can_approve = True
        else:
            contract = await self.bot.db.fetchrow(
                """SELECT can_hire FROM contracts 
                WHERE business_id = $1 AND employee_id = $2""",
                business["business_id"], ctx.author.id
            )
            if contract and contract["can_hire"]:
                can_approve = True

        if not can_approve:
            return await ctx.warn( "You don't have permission to approve applications!")

        application = await self.bot.db.fetchrow(
            """SELECT ja.*, bj.position, bj.salary, bj.business_id
            FROM job_applications ja
            JOIN business_jobs bj ON ja.job_id = bj.job_id
            WHERE ja.application_id = $1 AND bj.business_id = $2""",
            application_id, business["business_id"]
        )

        if not application:
            return await ctx.warn( "Application not found!")

        if application["status"] != "pending":
            return await ctx.warn( "This application has already been reviewed!")

        applicant = ctx.guild.get_member(application["applicant_id"])
        if not applicant:
            return await ctx.warn( "Applicant not found!")

        employee_count = await self.bot.db.fetchval(
            """SELECT COUNT(*) FROM contracts WHERE business_id = $1""",
            business["business_id"]
        )
        
        if employee_count >= business["employee_limit"]:
            return await ctx.warn( "Your business has reached its employee limit!")

        async with self.bot.db.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """INSERT INTO contracts (
                        business_id, employee_id, salary, position
                    ) VALUES ($1, $2, $3, $4)""",
                    business["business_id"], applicant.id,
                    application["salary"], application["position"]
                )
                
                await conn.execute(
                    """UPDATE job_applications 
                    SET status = 'approved', reviewed_by = $1, reviewed_at = CURRENT_TIMESTAMP 
                    WHERE application_id = $2""",
                    ctx.author.id, application_id
                )

        await ctx.approve(f"Hired {applicant.name} as {application['position']}!")
        try:
            await applicant.send(
                f"🎉 Congratulations! You've been hired at {business['name']} "
                f"as {application['position']} with a salary of {application['salary']:,}/hr!"
            )
        except:
            pass

    @business_hiring.command(name="deny")
    @is_econ_allowed()
    async def business_deny_application(self, ctx: Context, application_id: int):
        """Deny a job application"""
        business = await self.bot.db.fetchrow(
            """SELECT * FROM businesses WHERE owner_id = $1""",
            ctx.author.id
        )
        
        if not business:
            return await ctx.warn( "You don't own a business!")

        can_deny = False
        if ctx.author.id == business["owner_id"]:
            can_deny = True
        else:
            contract = await self.bot.db.fetchrow(
                """SELECT can_hire FROM contracts 
                WHERE business_id = $1 AND employee_id = $2""",
                business["business_id"], ctx.author.id
            )
            if contract and contract["can_hire"]:
                can_deny = True

        if not can_deny:
            return await ctx.warn( "You don't have permission to deny applications!")

        application = await self.bot.db.fetchrow(
            """SELECT ja.*, bj.position, bj.business_id
            FROM job_applications ja
            JOIN business_jobs bj ON ja.job_id = bj.job_id
            WHERE ja.application_id = $1 AND bj.business_id = $2""",
            application_id, business["business_id"]
        )

        if not application:
            return await ctx.warn( "Application not found!")

        if application["status"] != "pending":
            return await ctx.warn( "This application has already been reviewed!")

        await self.bot.db.execute(
            """UPDATE job_applications 
            SET status = 'denied', reviewed_by = $1, reviewed_at = CURRENT_TIMESTAMP 
            WHERE application_id = $2""",
            ctx.author.id, application_id
        )

        applicant = ctx.guild.get_member(application["applicant_id"])
        await ctx.approve(f"Denied {applicant.name}'s application!")
        
        if applicant:
            try:
                await applicant.send(
                    f"Your application for {application['position']} "
                    f"at {business['name']} has been denied."
                )
            except:
                pass

    @business_hiring.command(name="history")
    @is_econ_allowed()
    async def business_application_history(self, ctx: Context):
        """View application history for your business"""
        business = await self.bot.db.fetchrow(
            """SELECT * FROM businesses WHERE owner_id = $1""",
            ctx.author.id
        )
        
        if not business:
            return await ctx.warn( "You don't own a business!")

        history = await self.bot.db.fetch(
            """SELECT ja.*, bj.position, u.name as reviewer_name
            FROM job_applications ja
            JOIN business_jobs bj ON ja.job_id = bj.job_id
            LEFT JOIN users u ON ja.reviewed_by = u.user_id
            WHERE bj.business_id = $1 AND ja.status != 'pending'
            ORDER BY ja.reviewed_at DESC LIMIT 10""",
            business["business_id"]
        )

        if not history:
            return await ctx.warn( "No application history found!")

        embed = Embed(
            title=f"📜 Application History - {business['name']}",
            color=config.COLORS.NEUTRAL
        )

        for app in history:
            applicant = ctx.guild.get_member(app["applicant_id"])
            status_emoji = "✅" if app["status"] == "approved" else "❌"
            if applicant:
                embed.add_field(
                    name=f"{status_emoji} {applicant.name} - {app['position']}",
                    value=(
                        f"📅 Reviewed: {app['reviewed_at'].strftime('%Y-%m-%d')}\n"
                        f"👤 Reviewed by: {app['reviewer_name']}"
                    ),
                    inline=False
                )

        await ctx.send(embed=embed)

    @business_hiring.command(name="stats")
    @is_econ_allowed()
    async def business_hiring_stats(self, ctx: Context):
        """View hiring statistics for your business"""
        business = await self.bot.db.fetchrow(
            """SELECT * FROM businesses WHERE owner_id = $1""",
            ctx.author.id
        )
        
        if not business:
            return await ctx.warn( "You don't own a business!")

        stats = await self.bot.db.fetchrow(
            """SELECT 
                COUNT(*) as total_applications,
                COUNT(*) FILTER (WHERE status = 'approved') as approved,
                COUNT(*) FILTER (WHERE status = 'denied') as denied,
                COUNT(*) FILTER (WHERE status = 'pending') as pending
            FROM job_applications ja
            JOIN business_jobs bj ON ja.job_id = bj.job_id
            WHERE bj.business_id = $1""",
            business["business_id"]
        )

        embed = Embed(
            title=f"📊 Hiring Statistics - {business['name']}",
            color=config.COLORS.NEUTRAL
        )
        
        embed.add_field(
            name="Total Applications",
            value=f"{stats['total_applications']:,}",
            inline=True
        )
        embed.add_field(
            name="Approved",
            value=f"{stats['approved']:,}",
            inline=True
        )
        embed.add_field(
            name="Denied",
            value=f"{stats['denied']:,}",
            inline=True
        )
        embed.add_field(
            name="Pending",
            value=f"{stats['pending']:,}",
            inline=True
        )

        await ctx.send(embed=embed)

    @commands.group(name="shop", invoke_without_command=True)
    @is_econ_allowed()
    async def shop(self, ctx: Context):
        """View available items in the shop"""
        items = await self.bot.db.fetch(
            """SELECT * FROM shop_items ORDER BY price"""
        )

        embed = Embed(
            title="Item Shop",
            description="Use `shop buy <item>` to purchase",
            color=config.COLORS.NEUTRAL
        )

        for item in items:
            effect = f"{item['effect_value']}x {item['effect_type']}"
            if item['duration']:
                effect += f" for {item['duration']} hours"

            embed.add_field(
                name=f"{item['name']} - {item['price']:,} coins",
                value=f"📝 {item['description']}\n✨ Effect: {effect}",
                inline=False
            )

        await ctx.send(embed=embed)

    @shop.command(name="buy")
    @is_econ_allowed()
    async def shop_buy(self, ctx: Context, *, item_name: str):
        """Purchase an item from the shop"""
        item = await self.bot.db.fetchrow(
            """SELECT * FROM shop_items WHERE name = $1""",
            item_name
        )

        if not item:
            return await ctx.warn( "Item not found!")

        wallet, _, _ = await self.get_balance(ctx.author.id)
        if wallet < item["price"]:
            return await ctx.warn( 
                f"You need {item['price']:,} coins to buy this item!"
            )

        confirm = await ctx.prompt(
            f"Buy {item['name']} for {item['price']:,} coins?"
        )
        
        if not confirm:
            return await ctx.warn( "Purchase cancelled")

        expires_at = None
        if item["duration"]:
            expires_at = datetime.now(timezone.utc) + timedelta(
                hours=item["duration"]
            )

        await self.bot.db.execute(
            """INSERT INTO user_items (user_id, item_id, expires_at)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id, item_id) 
            DO UPDATE SET 
                quantity = user_items.quantity + 1,
                expires_at = $3""",
            ctx.author.id, item["item_id"], expires_at
        )

        await self.bot.db.execute(
            """UPDATE economy 
            SET wallet = wallet - $1 
            WHERE user_id = $2""",
            item["price"], ctx.author.id
        )

        await ctx.approve(f"Purchased {item['name']}!")

    @shop.group(name="role", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    @is_econ_allowed()
    async def role_shop(self, ctx: Context):
        """Manage the server's role shop"""
        await self.show_role_shop(ctx)

    async def show_role_shop(self, ctx: Context):
        """Helper function to display role shop"""
        roles = await self.bot.db.fetch(
            """SELECT * FROM role_shops WHERE guild_id = $1""",
            ctx.guild.id
        )

        if not roles:
            return await ctx.warn( "No roles in the shop!")

        embed = Embed(
            title="🎭 Role Shop",
            description="Use `shop buy <role>` to purchase",
            color=config.COLORS.NEUTRAL
        )

        for role_data in roles:
            role = ctx.guild.get_role(role_data["role_id"])
            if role:
                embed.add_field(
                    name=f"{role.name} - {role_data['price']:,} coins",
                    value=role_data["description"] or "No description",
                    inline=False
                )

        await ctx.send(embed=embed)

    @role_shop.command(name="add")
    @commands.has_permissions(administrator=True)
    @is_econ_allowed()
    async def role_shop_add(
        self, ctx: Context, role: discord.Role, price: int, *, description: str = None
    ):
        """Add a role to the role shop"""

        if role.is_default():
            return await ctx.warn( "You cannot add a price to the @everyone role") 

        if price < 0:
            return await ctx.warn( "Price must be positive!")

        await self.bot.db.execute(
            """INSERT INTO role_shops (guild_id, role_id, price, description)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (guild_id, role_id) DO UPDATE 
            SET price = $3, description = $4""",
            ctx.guild.id, role.id, price, description
        )

        await ctx.approve(f"Added {role.name} to the shop for {price:,} coins!")

    @role_shop.command(name="remove")
    @commands.has_permissions(administrator=True)
    @is_econ_allowed()
    async def role_shop_remove(self, ctx: Context, role: discord.Role):
        """Remove a role from the role shop"""
        result = await self.bot.db.execute(
            """DELETE FROM role_shops 
            WHERE guild_id = $1 AND role_id = $2""",
            ctx.guild.id, role.id
        )

        if result == "DELETE 0":
            return await ctx.warn( "That role isn't in the shop!")

        await ctx.approve(f"Removed {role.name} from the shop!")

    @shop.command(name="roles", aliases=["list"])
    async def shop_roles(self, ctx: Context):
        """List all roles in the server's role shop"""
        await self.show_role_shop(ctx)

    @role_shop.command(name="embed")
    @commands.has_permissions(administrator=True)
    @is_econ_allowed()
    async def role_shop_embed(self, ctx: Context, channel: discord.TextChannel = None):
        """Send role shop embed to specified channel"""
        channel = channel or ctx.channel
        roles = await self.bot.db.fetch(
            """SELECT * FROM role_shops WHERE guild_id = $1""",
            ctx.guild.id
        )

        if not roles:
            return await ctx.warn( "No roles in the shop!")

        embed = Embed(
            title="Server Role Shop",
            description="Purchase roles using `shop buy <role>`",
            color=config.COLORS.NEUTRAL
        )

        for role_data in roles:
            role = ctx.guild.get_role(role_data["role_id"])
            if role:
                embed.add_field(
                    name=f"{role.name} - {role_data['price']:,} coins",
                    value=role_data["description"] or "No description",
                    inline=False
                )

        await channel.send(embed=embed)
        if channel != ctx.channel:
            await ctx.approve(f"Sent role shop embed to {channel.mention}!")

    @shop.command(name="preview", aliases=["effects"])
    @is_econ_allowed()
    async def shop_preview(self, ctx: Context, *, item_name: str = None):
        """Preview item effects or view your active effects"""
        if item_name:
            item = await self.bot.db.fetchrow(
                """SELECT * FROM shop_items WHERE name = $1""",
                item_name
            )
            
            if not item:
                return await ctx.warn( "Item not found!")

            embed = Embed(
                title=f"🔮 {item['name']} Effect Preview",
                description=item["description"],
                color=config.COLORS.NEUTRAL
            )

            effect_info = self.effect_details.get(item["effect_type"])
            if effect_info:
                duration_text = (
                    f"{item['duration']} hours" 
                    if item['duration'] else "One-time use"
                )
                boost_percent = (item["effect_value"] - 1) * 100

                effect_desc = effect_info["description"].format(
                    boost_percent=f"{boost_percent:.0f}",
                    duration=duration_text
                )
                
                embed.add_field(
                    name="Effect Details",
                    value=effect_desc,
                    inline=False
                )

                if effect_info["example"]:
                    base = effect_info["example"]["base"]
                    boosted = base * item["effect_value"]
                    example = effect_info["example"]["format"].format(
                        base=base,
                        boosted=boosted,
                        name=item["name"]
                    )
                    
                    embed.add_field(
                        name="Practical Example",
                        value=f"**Example:**\n{example}",
                        inline=False
                    )

            embed.add_field(
                name="Price",
                value=f"{item['price']:,} coins",
                inline=True
            )

        else:
            effects = await self.get_active_effects(ctx.author.id)
            
            if not effects:
                return await ctx.warn( "You have no active effects!")

            embed = Embed(
                title="🎭 Your Active Effects",
                color=config.COLORS.NEUTRAL
            )

            for effect_type, data in effects.items():
                effect_info = self.effect_details.get(effect_type)
                if effect_info:
                    name = effect_info["name"]
                    value = data["value"]
                    expires = data["expires"]

                    if expires:
                        time_left = expires - datetime.now(timezone.utc)
                        hours_left = int(time_left.total_seconds() / 3600)
                        status = f"Expires in {hours_left}h"
                    else:
                        status = "One-time use"

                    boost_percent = (value - 1) * 100
                    embed.add_field(
                        name=name,
                        value=(
                            f"Boost: {boost_percent:+.0f}%\n"
                            f"Status: {status}"
                        ),
                        inline=False
                    )

        await ctx.send(embed=embed)

    @shop.command(name="inventory", aliases=["inv"])
    @is_econ_allowed()
    async def shop_inventory(self, ctx: Context):
        """View your purchased items"""
        items = await self.bot.db.fetch(
            """SELECT ui.*, si.name, si.description, 
                si.effect_type, si.effect_value, si.duration
            FROM user_items ui
            JOIN shop_items si ON ui.item_id = si.item_id
            WHERE ui.user_id = $1 AND ui.quantity > 0""",
            ctx.author.id
        )

        if not items:
            return await ctx.warn( "You don't have any items!")

        embed = Embed(
            title="🎒 Your Inventory",
            description="View item effects with `shop preview <item>`",
            color=config.COLORS.NEUTRAL
        )

        for item in items:
            status = "Ready to use"
            if item["expires_at"]:
                if item["expires_at"] < datetime.now(timezone.utc):
                    continue
                else:
                    time_left = item["expires_at"] - datetime.now(timezone.utc)
                    hours_left = int(time_left.total_seconds() / 3600)
                    status = f"Active - {hours_left}h remaining"

            effect_info = self.effect_details.get(item["effect_type"])
            if effect_info:
                boost_percent = (item["effect_value"] - 1) * 100
                effect_text = effect_info["description"].format(
                    boost_percent=f"{boost_percent:.0f}",
                    duration=f"{item['duration']} hours" if item["duration"] else "One-time"
                )
            else:
                effect_text = f"{item['effect_value']}x {item['effect_type']}"

            embed.add_field(
                name=f"{item['name']} (x{item['quantity']})",
                value=(
                    f"📝 {item['description']}\n"
                    f"⚡ Effect: {effect_text}\n"
                    f"⏳ Status: {status}"
                ),
                inline=False
            )

        if items:
            embed.set_footer(
                text="Items with duration will activate automatically when purchased. "
                "One-time items will be used on your next eligible action."
            )

        await ctx.send(embed=embed)

    async def setup_default_shop_items(self):
        """Initialize default shop items and their effects"""
        default_items = [
            {
                "name": "Lucky Charm",
                "description": "Increases gambling win chances by 50% for 24 hours",
                "price": 50000,
                "effect_type": "gambling_luck",
                "effect_value": 1.5,
                "duration": 24,
                "effect_description": (
                    "🎲 **Gambling**\n"
                    "• Win chance increased by {boost_percent}%\n"
                    "• Duration: {duration}"
                ),
                "example": {
                    "base": 50,
                    "format": (
                        "Normal coin flip: {base}% chance\n"
                        "With {name}: {boosted}% chance"
                    )
                }
            },
            {
                "name": "Money Magnet",
                "description": "Increases all earnings by 25% for 12 hours",
                "price": 75000,
                "effect_type": "earnings_boost",
                "effect_value": 1.25,
                "duration": 12,
                "effect_description": (
                    "💰 **All Earnings**\n"
                    "• Increased by {boost_percent}%\n"
                    "• Duration: {duration}"
                ),
                "example": {
                    "base": 1000,
                    "format": (
                        "Normal earnings: {base:,} coins\n"
                        "With {name}: {boosted:,} coins"
                    )
                }
            },
            {
                "name": "Golden Ticket",
                "description": "Doubles your next gambling win (one-time use)",
                "price": 100000,
                "effect_type": "next_gamble_multiplier",
                "effect_value": 2.0,
                "duration": None
            },
            {
                "name": "Royal Pass",
                "description": "Access to high-stakes gambling tables for 48 hours",
                "price": 250000,
                "effect_type": "high_stakes_access",
                "effect_value": 1.0,
                "duration": 48
            },
            {
                "name": "Business Booster",
                "description": "Increases business revenue by 40% for 24 hours",
                "price": 150000,
                "effect_type": "business_boost",
                "effect_value": 1.4,
                "duration": 24
            },
            {
                "name": "Jackpot Jewel",
                "description": "10% chance for 5x payout on your next win",
                "price": 200000,
                "effect_type": "jackpot_chance",
                "effect_value": 5.0,
                "duration": None
            },
            {
                "name": "Daily Doubler",
                "description": "Doubles your next daily reward",
                "price": 25000,
                "effect_type": "daily_boost",
                "effect_value": 2.0,
                "duration": None
            },
            {
                "name": "Work Whistle",
                "description": "Reduces work command cooldown by 50% for 12 hours",
                "price": 40000,
                "effect_type": "work_cooldown",
                "effect_value": 0.5,
                "duration": 12
            },
            {
                "name": "Rich Ritual",
                "description": "All earnings go straight to bank for 6 hours",
                "price": 30000,
                "effect_type": "auto_bank",
                "effect_value": 1.0,
                "duration": 6
            },
            {
                "name": "Midas Touch",
                "description": "15% chance to double any earnings for 24 hours",
                "price": 125000,
                "effect_type": "random_double",
                "effect_value": 2.0,
                "duration": 24
            }
        ]

        self.effect_details = {}
        for item in default_items:
            await self.bot.db.execute(
                """INSERT INTO shop_items (
                    name, description, price, 
                    effect_type, effect_value, duration,
                    effect_description, effect_example
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (name) DO NOTHING""",
                item["name"], 
                item["description"], 
                item["price"],
                item["effect_type"], 
                item["effect_value"], 
                item["duration"],
                item.get("effect_description"),  
                json.dumps(item.get("example")) if "example" in item else None
            )
            
            if "effect_description" in item:
                self.effect_details[item["effect_type"]] = {
                    "description": item["effect_description"],
                    "example": item.get("example"),
                    "name": item["name"]
                }

    @shop.command(name="gift")
    @is_econ_allowed()
    @max_concurrency(1, BucketType.user) 
    async def shop_gift(self, ctx: Context, user: Member, *, item_name: str):
        """Gift an item from your inventory to another user (3 per hour, 10 per day)"""
        if user.bot:
            return await ctx.warn( "You can't gift items to bots!")
            
        if user.id == ctx.author.id:
            return await ctx.warn( "You can't gift items to yourself!")

        bucket_key = f"{ctx.author.id}:daily_gifts"
        daily_gifts = await self.bot.redis.incr(bucket_key)
        
        if daily_gifts == 1:  
            await self.bot.redis.expire(bucket_key, 86400)  
        
        if daily_gifts > 10:
            await self.bot.redis.decr(bucket_key)  
            return await ctx.warn( 
                "You've reached your daily gift limit! (10 gifts per day)\n"
                "The limit resets at midnight UTC."
            )

        receiver_key = f"{user.id}:received_gifts"
        received_gifts = await self.bot.redis.incr(receiver_key)
        
        if received_gifts == 1:  
            await self.bot.redis.expire(receiver_key, 86400) 
            
        if received_gifts > 5:
            await self.bot.redis.decr(receiver_key) 
            return await ctx.warn( 
                f"{user.name} has reached their daily received gift limit!\n"
                "They can receive more gifts after midnight UTC."
            )

        item_data = await self.bot.db.fetchrow(
            """SELECT ui.quantity, ui.expires_at, si.* 
            FROM user_items ui
            JOIN shop_items si ON ui.item_id = si.item_id
            WHERE ui.user_id = $1 AND si.name = $2""",
            ctx.author.id, item_name
        )

        if not item_data:
            return await ctx.warn( "You don't own this item!")

        if item_data["quantity"] <= 0:
            return await ctx.warn( "You don't have any of this item left!")

        if item_data["expires_at"]:
            if item_data["expires_at"] < datetime.now(timezone.utc):
                return await ctx.warn( "This item has expired!")
            return await ctx.warn( "You can't gift active items!")

        confirm = await ctx.prompt(
            f"Gift 1x {item_data['name']} to {user.name}?"
        )
        
        if not confirm:
            return await ctx.warn( "Gift cancelled")

        async with self.bot.db.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """UPDATE user_items 
                    SET quantity = quantity - 1 
                    WHERE user_id = $1 AND item_id = $2""",
                    ctx.author.id, item_data["item_id"]
                )

                await conn.execute(
                    """INSERT INTO user_items (user_id, item_id, quantity)
                    VALUES ($1, $2, 1)
                    ON CONFLICT (user_id, item_id) 
                    DO UPDATE SET quantity = user_items.quantity + 1""",
                    user.id, item_data["item_id"]
                )

                await conn.execute(
                    """INSERT INTO gift_logs (
                        sender_id, receiver_id, item_id, quantity
                    ) VALUES ($1, $2, $3, 1)""",
                    ctx.author.id, user.id, item_data["item_id"]
                )

        remaining_gifts = 10 - (daily_gifts - 1)
        cooldown = ctx.command._buckets.get_bucket(ctx)
        remaining_cooldown = cooldown._window - (time.time() - cooldown._last)
        next_gift_in = f"{remaining_cooldown/60:.1f} minutes" if remaining_cooldown > 0 else "now"

        await ctx.approve(
            f"Gifted {item_data['name']} to {user.name}!\n"
            f"Daily gifts remaining: {remaining_gifts}\n"
            f"Next gift available: {next_gift_in}"
        )

        try:
            effect_info = self.effect_details.get(item_data["effect_type"])
            if effect_info:
                boost_percent = (item_data["effect_value"] - 1) * 100
                effect_text = effect_info["description"].format(
                    boost_percent=f"{boost_percent:.0f}",
                    duration="one-time use"
                )
            else:
                effect_text = f"{item_data['effect_value']}x {item_data['effect_type']}"

            await user.send(
                f"🎁 {ctx.author.name} has gifted you a {item_data['name']}!\n"
                f"📝 {item_data['description']}\n"
                f"⚡ Effect: {effect_text}"
            )
        except:
            pass

    @shop.command(name="giftlimit")
    @is_econ_allowed()
    async def gift_limit(self, ctx: Context):
        """Check your remaining gift limits"""
        daily_gifts = int(
            await self.bot.redis.get(f"{ctx.author.id}:daily_gifts") or 0
        )
        received_gifts = int(
            await self.bot.redis.get(f"{ctx.author.id}:received_gifts") or 0
        )

        bucket = self.shop_gift._buckets.get_bucket(ctx)
        retry_after = bucket.get_retry_after()
        
        if retry_after:
            next_gift = f"in {retry_after/60:.1f} minutes"
        else:
            next_gift = "now"

        embed = Embed(
            title="🎁 Gift Limits",
            color=config.COLORS.NEUTRAL
        )

        embed.add_field(
            name="Sending Gifts",
            value=(
                f"Daily gifts sent: {daily_gifts}/10\n"
                f"Remaining today: {10 - daily_gifts}\n"
                f"Next gift available: {next_gift}"
            ),
            inline=False
        )

        embed.add_field(
            name="Receiving Gifts",
            value=(
                f"Daily gifts received: {received_gifts}/5\n"
                f"Can receive {5 - received_gifts} more today"
            ),
            inline=False
        )

        embed.set_footer(text="Limits reset at midnight UTC")
        await ctx.send(embed=embed)

    @commands.group(name="gamble", invoke_without_command=True)
    @is_econ_allowed()
    async def gamble(self, ctx: Context):
        """
        View available gambling games.
        """
        embed = Embed(
            title=f"{config.EMOJIS.ECONOMY.INVIS}{config.EMOJIS.ECONOMY.INVIS}{config.EMOJIS.ECONOMY.INVIS}{config.EMOJIS.ECONOMY.INVIS}Game Center",
            description=(
                "**:game_die: Dice Games:** `normal` | `higher` | `match`\n"
                "**:coin: Coinflip:** `coinflip` – 2x payout\n"
                "**:slot_machine: Slots:** `slots` – Multi-line wins\n"
                "**:spades: Blackjack:** `blackjack` – Beat the dealer\n"
                "**:ferris_wheel: Wheel:** `wheel` – Spin to win\n"
                "**:game_die: Roulette:** `roulette` – Bet & win\n"
                "**:chart_with_upwards_trend: Crash:** `crash` – Cash out in time\n"
                "**:arrow_up_down: Over/Under:** `overunder` – Guess high or low\n"
                "**:tickets: Scratch Card:** `scratch` – Reveal to win\n"
                "**:spades: Poker:** `poker` – Test your luck\n"
                "**:horse_racing: Horse Race:** `race` – Bet on winners\n"
                "**:ladder: Money Ladder:** `ladder` – Climb for multipliers\n"
                "**:bomb: Mines:** `mines` – Avoid explosions\n"
            ),
            color=config.COLORS.NEUTRAL
        )
        await ctx.send(embed=embed)

    @gamble.command(name="coinflip", aliases=["cf"])
    @is_econ_allowed()
    @commands.cooldown(1, 3, BucketType.user)
    async def gamble_coinflip(self, ctx: Context, choice: str, amount: str):
        """
        Flip a coin and double your money! (h/t or heads/tails).
        """
        choice = choice.lower()
        if choice not in ['h', 't', 'heads', 'tails']:
            return await ctx.warn( "Please choose `heads` or `tails` (or `h`/`t`)")

        if amount.lower() == 'all':
            wallet, _, _ = await self.get_balance(ctx.author.id)
            amount = wallet
        else:
            try:
                amount = int(amount.replace(',', ''))
            except ValueError:
                return await ctx.warn( "Please provide a valid amount or `all`")

        if amount < 100:
            return await ctx.warn( "Minimum bet is 100 coins!")

        daily_gambled = int(await self.bot.redis.get(f"daily_gambled:{ctx.author.id}") or 0)
        daily_limit = 1_000_000  
        if daily_gambled + amount > daily_limit:
            remaining = daily_limit - daily_gambled
            return await ctx.warn( 
                f"Daily gambling limit reached! You can only gamble {remaining:,} more coins today."
            )

        house_edge = min(0.05 + (amount / 1_000_000) * 0.15, 0.25)  
        base_chance = 0.5 * (1 - house_edge)
        
        win_streak = int(await self.bot.redis.get(f"win_streak:{ctx.author.id}") or 0)
        if win_streak > 3:  
            base_chance *= 0.8  

        wallet, _, _ = await self.get_balance(ctx.author.id)
        if amount > wallet:
            return await ctx.warn( "You don't have enough coins!")

        effects = await self.get_active_effects(ctx.author.id)
        luck_boost = effects.get('gambling_luck', {'value': 1.0})['value']
        win_multiplier = effects.get('next_gamble_multiplier', {'value': 2.0})['value']

        embed = Embed(title="🪙 Coinflip", color=discord.Color.gold())
        embed.add_field(
            name="Your Bet",
            value=f"**{amount:,}** coins on **{choice}**"
        )
        if luck_boost > 1.0:
            embed.add_field(
                name="🍀 Luck Boost",
                value=f"+{(luck_boost-1)*100:.0f}% win chance"
            )

        msg = await ctx.send(embed=embed)

        flips = ['heads', 'tails'] * 3
        for flip in flips:
            embed.description = f"Flipping... **{flip}**!"
            await msg.edit(embed=embed)
            await asyncio.sleep(0.5)

        base_chance = 0.5
        win_chance = min(base_chance * luck_boost, 0.75) 
        result = 'heads' if random.random() < 0.5 else 'tails'
        
        choice = 'heads' if choice in ['h', 'heads'] else 'tails'
        won = choice == result

        async with self.bot.db.acquire() as conn:
            async with conn.transaction():
                if won:
                    win_amount = int(amount * win_multiplier)
                    await conn.execute(
                        """UPDATE economy 
                        SET wallet = wallet + $1 
                        WHERE user_id = $2""",
                        win_amount - amount, ctx.author.id
                    )
                    if win_multiplier > 2.0:
                        await self.use_one_time_effect(
                            ctx.author.id, 'next_gamble_multiplier'
                        )
                    await self.log_transaction(ctx.author.id, "gamble_win", win_amount)
                    
                    await self.bot.redis.incr(f"win_streak:{ctx.author.id}")
                    await self.bot.redis.expire(f"win_streak:{ctx.author.id}", 3600)  
                else:
                    await conn.execute(
                        """UPDATE economy 
                        SET wallet = wallet - $1 
                        WHERE user_id = $2""",
                        amount, ctx.author.id
                    )
                    await self.log_transaction(ctx.author.id, "gamble_loss", -amount)
                    await self.bot.redis.delete(f"win_streak:{ctx.author.id}")

                await self.bot.redis.incrby(f"daily_gambled:{ctx.author.id}", amount)
                if daily_gambled == 0: 
                    await self.bot.redis.expire(f"daily_gambled:{ctx.author.id}", 86400)  

        embed.description = (
            f"The coin landed on **{result}**!\n\n"
            f"{'🎉 You won' if won else '😢 You lost'} "
            f"**{amount:,}** coins!"
        )
        if won and win_multiplier > 2.0:
            embed.description += f"\n🌟 Multiplier bonus: {win_multiplier}x"
        
        await msg.edit(embed=embed)

    @commands.group(name="lottery", aliases=["lotto"], invoke_without_command=True)
    @is_econ_allowed()
    async def lottery(self, ctx, amount: int = None):
        """Enter the lottery with coins"""
        total_pot = int(await self.bot.redis.get("lottery:pot") or 0)
        total_tickets = int(await self.bot.redis.get("lottery:total_tickets") or 1)
        user_tickets = int(await self.bot.redis.get(f"lottery:tickets:{ctx.author.id}") or 0)
        next_draw = await self.bot.redis.get("lottery:next_draw")

        if not next_draw:
            next_draw = datetime.now(timezone.utc) + timedelta(days=1)
            await self.bot.redis.set("lottery:next_draw", next_draw.timestamp())
            next_draw = datetime.fromtimestamp(next_draw.timestamp(), timezone.utc)
        else:
            next_draw = datetime.fromtimestamp(float(next_draw), timezone.utc)
            if next_draw < datetime.now(timezone.utc):
                next_draw = datetime.now(timezone.utc) + timedelta(days=1)
                await self.bot.redis.set("lottery:next_draw", next_draw.timestamp())

        time_left = next_draw - datetime.now(timezone.utc)
        hours, remainder = divmod(max(int(time_left.total_seconds()), 0), 3600)
        minutes, seconds = divmod(remainder, 60)
        winning_chance = (user_tickets / total_tickets) * 100 if user_tickets > 0 else 0

        if amount is None:
            embed = Embed(
                title="🎰 Daily Lottery",
                description="Enter with `;lottery <amount>`\nLottery ends once a day! The maximum lottery submission is 250k coins!",
                color=discord.Color.gold()
            )
            embed.add_field(name="You added", value=f"{user_tickets:,} coins", inline=True)
            embed.add_field(name="Your Total Submission", value=f"{user_tickets:,} coins", inline=True)
            embed.add_field(name="Winning Chance", value=f"{winning_chance:.10f}%", inline=True)
            embed.add_field(name="Current Jackpot", value=f"{total_pot:,} coins", inline=True)
            embed.add_field(name="Ends in", value=f"{hours}h {minutes}m {seconds}s", inline=True)
            embed.set_footer(text="*Percentage and jackpot may change over time")
            return await ctx.send(embed=embed)

        if amount <= 0:
            return await ctx.warn( "Amount must be positive!")
        if amount > 250_000:
            return await ctx.warn( "Maximum lottery submission is 250,000 coins!")
        if user_tickets + amount > 250_000:
            return await ctx.warn( "You can't submit more than 250,000 coins total!")

        wallet = await self.bot.db.fetchval(
            """SELECT wallet FROM economy WHERE user_id = $1""",
            ctx.author.id
        )
        if not wallet or wallet < amount:
            return await ctx.warn( "You don't have enough coins!")

        async with self.bot.db.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """UPDATE economy SET wallet = wallet - $1 WHERE user_id = $2""",
                    amount, ctx.author.id
                )
                pipe = self.bot.redis.pipeline()
                pipe.incrby(f"lottery:tickets:{ctx.author.id}", amount)
                pipe.incrby("lottery:total_tickets", amount)
                pipe.incrby("lottery:pot", amount)
                await pipe.execute()

        total_pot += amount
        total_tickets += amount
        user_tickets += amount
        winning_chance = (user_tickets / total_tickets) * 100

        embed = Embed(
            title="🎰 Lottery Submission",
            description="Lottery ends once a day! The maximum lottery submission is 250k coins!",
            color=discord.Color.gold()
        )
        embed.add_field(name="You added", value=f"{amount:,} coins", inline=True)
        embed.add_field(name="Your Total Submission", value=f"{user_tickets:,} coins", inline=True)
        embed.add_field(name="Winning Chance", value=f"{winning_chance:.10f}%", inline=True)
        embed.add_field(name="Current Jackpot", value=f"{total_pot:,} coins", inline=True)
        embed.add_field(name="Ends in", value=f"{hours}h {minutes}m {seconds}s", inline=True)
        embed.set_footer(text="*Percentage and jackpot may change over time • Today at " + 
                        datetime.now().strftime("%I:%M %p"))
        await ctx.send(embed=embed)

    @lottery.command(name="info")
    async def lottery_info(self, ctx):
        """View detailed lottery information and rules"""
        embed = Embed(
            title="🎰 Lottery Information",
            description="Daily lottery system information and rules",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="How it works",
            value="• Lottery draws happen once every 24 hours\n"
                  "• Each coin submitted = 1 ticket\n"
                  "• Maximum 250,000 tickets per user\n"
                  "• Winner takes the entire pot!\n"
                  "• Winning chance = your tickets / total tickets",
            inline=False
        )
        await ctx.send(embed=embed)

    @lottery.command(name="stats")
    async def lottery_stats(self, ctx):
        """View lottery statistics"""
        stats = await self.bot.db.fetchrow(
            """WITH user_stats AS (
                SELECT 
                    user_id,
                    COUNT(*) as wins,
                    SUM(pot_amount) as total_won
                FROM lottery_history
                GROUP BY user_id
                ORDER BY total_won DESC
                LIMIT 1
            )
            SELECT 
                COUNT(*) as total_draws,
                MAX(pot_amount) as biggest_pot,
                SUM(pot_amount) as total_awarded,
                us.user_id as top_winner_id,
                us.wins as top_winner_wins,
                us.total_won as top_winner_amount
            FROM lottery_history
            CROSS JOIN user_stats us""")
        
        top_winner = self.bot.get_user(stats['top_winner_id']) if stats['top_winner_id'] else None
        
        embed = Embed(title="📊 Lottery Statistics", color=discord.Color.gold())
        embed.add_field(name="Total Draws", value=f"{stats['total_draws']:,}")
        embed.add_field(name="Biggest Pot", value=f"{stats['biggest_pot']:,} coins")
        embed.add_field(name="Total Awarded", value=f"{stats['total_awarded']:,} coins")
        
        if top_winner:
            embed.add_field(
                name="Top Winner",
                value=(
                    f"{top_winner.name}\n"
                    f"Wins: {stats['top_winner_wins']:,}\n"
                    f"Total Won: {stats['top_winner_amount']:,} coins"
                ),
                inline=False
            )
        
        await ctx.send(embed=embed)

    @lottery.command(name="winners")
    async def lottery_winners(self, ctx):
        """View recent lottery winners"""
        winners = await self.bot.db.fetch(
            """SELECT 
                user_id,
                pot_amount,
                total_tickets,
                winner_tickets,
                won_at
            FROM lottery_history 
            ORDER BY won_at DESC 
            LIMIT 5"""
        )
        
        embed = Embed(title="👑 Recent Lottery Winners", color=discord.Color.gold())
        for winner in winners:
            user = self.bot.get_user(winner['user_id'])
            win_chance = (winner['winner_tickets'] / winner['total_tickets']) * 100
            embed.add_field(
                name=f"{user.name if user else 'Unknown User'}",
                value=(
                    f"Won {winner['pot_amount']:,} coins\n"
                    f"Winning Chance: {win_chance:.2f}%\n"
                    f"{discord.utils.format_dt(winner['won_at'], 'R')}"
                ),
                inline=False
            )
        await ctx.send(embed=embed)

    @gamble.group(name="dice", invoke_without_command=True)
    @is_econ_allowed()
    async def gamble_dice(self, ctx: Context):
        """View available dice games"""
        embed = Embed(
            title="🎲 Dice Games",
            description=(
                "**Available Games:**\n"
                "`dice normal <amount>` - Roll 1-6, double money on 4+\n"
                "`dice higher <amount>` - Bet if next roll is higher\n"
                "`dice match <number> <amount>` - 5x money on exact match"
            ),
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)

    @gamble_dice.command(name="normal")
    @is_econ_allowed()
    @commands.cooldown(1, 3, BucketType.user)
    async def dice_normal(self, ctx: Context, amount: str):
        """Roll 1-6, win on 4 or higher"""
        if amount.lower() == 'all':
            wallet, _, _ = await self.get_balance(ctx.author.id)
            amount = wallet
        else:
            try:
                amount = int(amount.replace(',', ''))
            except ValueError:
                return await ctx.warn( "Please provide a valid amount or `all`")

        if amount < 100:
            return await ctx.warn( "Minimum bet is 100 coins!")

        daily_gambled = int(await self.bot.redis.get(f"daily_gambled:{ctx.author.id}") or 0)
        daily_limit = 1_000_000
        if daily_gambled + amount > daily_limit:
            remaining = daily_limit - daily_gambled
            return await ctx.warn( 
                f"Daily gambling limit reached! You can only gamble {remaining:,} more coins today."
            )

        house_edge = min(0.05 + (amount / 1_000_000) * 0.15, 0.25)
        base_chance = 0.40 * (1 - house_edge)
        
        win_streak = int(await self.bot.redis.get(f"win_streak:{ctx.author.id}") or 0)
        if win_streak > 3:
            base_chance *= 0.8

        wallet, _, _ = await self.get_balance(ctx.author.id)
        if amount > wallet:
            return await ctx.warn( "You don't have enough coins!")

        effects = await self.get_active_effects(ctx.author.id)
        luck_boost = effects.get('gambling_luck', {'value': 1.0})['value']
        win_multiplier = effects.get('next_gamble_multiplier', {'value': 2.0})['value']

        embed = Embed(title="🎲 Dice Roll", color=discord.Color.gold())
        embed.add_field(
            name="Your Bet",
            value=f"**{amount:,}** coins"
        )
        if luck_boost > 1.0:
            embed.add_field(
                name="🍀 Luck Boost",
                value=f"+{(luck_boost-1)*100:.0f}% win chance"
            )

        msg = await ctx.send(embed=embed)

        for _ in range(3):
            roll = random.randint(1, 6)
            embed.description = f"Rolling... **{roll}**!"
            await msg.edit(embed=embed)
            await asyncio.sleep(0.5)

        # CHECKPOINT, % OF WINNING FOR DICE NORMAL    

        base_chance = 0.40  
        win_chance = min(base_chance * luck_boost, 0.60)  
        won = random.random() < win_chance
        final_roll = random.randint(4, 6) if won else random.randint(1, 3)

        async with self.bot.db.acquire() as conn:
            async with conn.transaction():
                if won:
                    win_amount = int(amount * win_multiplier)
                    await conn.execute(
                        """UPDATE economy 
                        SET wallet = wallet + $1 
                        WHERE user_id = $2""",
                        win_amount - amount, ctx.author.id
                    )
                    if win_multiplier > 2.0:
                        await self.use_one_time_effect(
                            ctx.author.id, 'next_gamble_multiplier'
                        )
                    await self.log_transaction(ctx.author.id, "gamble_win", win_amount)
                    
                    await self.bot.redis.incr(f"win_streak:{ctx.author.id}")
                    await self.bot.redis.expire(f"win_streak:{ctx.author.id}", 3600)  
                else:
                    await conn.execute(
                        """UPDATE economy 
                        SET wallet = wallet - $1 
                        WHERE user_id = $2""",
                        amount, ctx.author.id
                    )
                    await self.log_transaction(ctx.author.id, "gamble_loss", -amount)
                    await self.bot.redis.delete(f"win_streak:{ctx.author.id}")

                await self.bot.redis.incrby(f"daily_gambled:{ctx.author.id}", amount)
                if daily_gambled == 0: 
                    await self.bot.redis.expire(f"daily_gambled:{ctx.author.id}", 86400)  

        embed.description = (
            f"🎲 You rolled a **{final_roll}**!\n\n"
            f"{'🎉 You won' if won else '😢 You lost'} "
            f"**{amount:,}** coins!"
        )
        if won and win_multiplier > 2.0:
            embed.description += f"\n🌟 Multiplier bonus: {win_multiplier}x"

        await msg.edit(embed=embed)

    @gamble_dice.command(name="match")
    @is_econ_allowed()
    @commands.cooldown(1, 3, BucketType.user)
    async def dice_match(self, ctx: Context, number: int, amount: str):
        """Match the exact number for 5x payout"""
        if number < 1 or number > 6:
            return await ctx.warn( "Please choose a number between 1 and 6!")

        if amount.lower() == 'all':
            wallet, _, _ = await self.get_balance(ctx.author.id)
            amount = wallet
        else:
            try:
                amount = int(amount.replace(',', ''))
            except ValueError:
                return await ctx.warn( "Please provide a valid amount or `all`")

        if amount < 100:
            return await ctx.warn( "Minimum bet is 100 coins!")

        daily_gambled = int(await self.bot.redis.get(f"daily_gambled:{ctx.author.id}") or 0)
        daily_limit = 1_000_000
        if daily_gambled + amount > daily_limit:
            remaining = daily_limit - daily_gambled
            return await ctx.warn( 
                f"Daily gambling limit reached! You can only gamble {remaining:,} more coins today."
            )

        house_edge = min(0.05 + (amount / 1_000_000) * 0.15, 0.25)
        base_chance = (1/8) * (1 - house_edge)
        
        win_streak = int(await self.bot.redis.get(f"win_streak:{ctx.author.id}") or 0)
        if win_streak > 3:
            base_chance *= 0.8

        wallet, _, _ = await self.get_balance(ctx.author.id)
        if amount > wallet:
            return await ctx.warn( "You don't have enough coins!")

        effects = await self.get_active_effects(ctx.author.id)
        luck_boost = effects.get('gambling_luck', {'value': 1.0})['value']
        win_multiplier = effects.get('next_gamble_multiplier', {'value': 5.0})['value']

        embed = Embed(title="🎲 Dice Match", color=discord.Color.gold())
        embed.add_field(
            name="Your Bet",
            value=f"**{amount:,}** coins on **{number}**"
        )
        if luck_boost > 1.0:
            embed.add_field(
                name="🍀 Luck Boost",
                value=f"+{(luck_boost-1)*100:.0f}% win chance"
            )

        msg = await ctx.send(embed=embed)

        for _ in range(3):
            roll = random.randint(1, 6)
            embed.description = f"Rolling... **{roll}**!"
            await msg.edit(embed=embed)
            await asyncio.sleep(0.5)

        # CHECKPOINT, % OF WINNING FOR DICE MATCH    

        base_chance = 1/8
        win_chance = min(base_chance * luck_boost, 0.60) 
        won = random.random() < win_chance
        final_roll = number if won else random.choice([x for x in range(1, 7) if x != number])

        async with self.bot.db.acquire() as conn:
            async with conn.transaction():
                if won:
                    win_amount = int(amount * win_multiplier)
                    await conn.execute(
                        """UPDATE economy 
                        SET wallet = wallet + $1 
                        WHERE user_id = $2""",
                        win_amount - amount, ctx.author.id
                    )
                    if win_multiplier > 5.0:
                        await self.use_one_time_effect(
                            ctx.author.id, 'next_gamble_multiplier'
                        )
                    await self.log_transaction(ctx.author.id, "gamble_win", win_amount)
                    
                    await self.bot.redis.incr(f"win_streak:{ctx.author.id}")
                    await self.bot.redis.expire(f"win_streak:{ctx.author.id}", 3600)
                else:
                    await conn.execute(
                        """UPDATE economy 
                        SET wallet = wallet - $1 
                        WHERE user_id = $2""",
                        amount, ctx.author.id
                    )
                    await self.log_transaction(ctx.author.id, "gamble_loss", -amount)
                    await self.bot.redis.delete(f"win_streak:{ctx.author.id}")

                await self.bot.redis.incrby(f"daily_gambled:{ctx.author.id}", amount)
                if daily_gambled == 0:
                    await self.bot.redis.expire(f"daily_gambled:{ctx.author.id}", 86400)

        embed.description = (
            f"🎲 You rolled a **{final_roll}**!\n\n"
            f"{'🎉 You won' if won else '😢 You lost'} "
            f"**{amount:,}** coins!"
        )
        if won and win_multiplier > 5.0:
            embed.description += f"\n🌟 Multiplier bonus: {win_multiplier}x"

        await msg.edit(embed=embed)

    @gamble_dice.command(name="higher")
    @is_econ_allowed()
    @commands.cooldown(1, 3, BucketType.user)
    async def dice_higher(self, ctx: Context, amount: str):
        """Bet if the next roll will be higher"""
        if amount.lower() == 'all':
            wallet, _, _ = await self.get_balance(ctx.author.id)
            amount = wallet
        else:
            try:
                amount = int(amount.replace(',', ''))
            except ValueError:
                return await ctx.warn( "Please provide a valid amount or `all`")

        if amount < 100:
            return await ctx.warn( "Minimum bet is 100 coins!")

        daily_gambled = int(await self.bot.redis.get(f"daily_gambled:{ctx.author.id}") or 0)
        daily_limit = 1_000_000
        if daily_gambled + amount > daily_limit:
            remaining = daily_limit - daily_gambled
            return await ctx.warn( 
                f"Daily gambling limit reached! You can only gamble {remaining:,} more coins today."
            )

        house_edge = min(0.05 + (amount / 1_000_000) * 0.15, 0.25)
        base_chance = 0.5 * (1 - house_edge)
        
        win_streak = int(await self.bot.redis.get(f"win_streak:{ctx.author.id}") or 0)
        if win_streak > 3:
            base_chance *= 0.8

        wallet, _, _ = await self.get_balance(ctx.author.id)
        if amount > wallet:
            return await ctx.warn( "You don't have enough coins!")

        effects = await self.get_active_effects(ctx.author.id)
        luck_boost = effects.get('gambling_luck', {'value': 1.0})['value']
        win_multiplier = effects.get('next_gamble_multiplier', {'value': 2.0})['value']

        embed = Embed(title="🎲 Higher or Lower", color=discord.Color.gold())
        first_roll = random.randint(1, 6)
        embed.description = f"First roll: **{first_roll}**\nWill the next roll be higher?"
        embed.add_field(
            name="Your Bet",
            value=f"**{amount:,}** coins"
        )
        if luck_boost > 1.0:
            embed.add_field(
                name="🍀 Luck Boost",
                value=f"+{(luck_boost-1)*100:.0f}% win chance"
            )

        msg = await ctx.send(embed=embed)
        await msg.add_reaction("👍")  
        await msg.add_reaction("👎")  

        try:
            reaction, user = await ctx.bot.wait_for(
                'reaction_add',
                timeout=15.0,
                check=lambda r, u: u == ctx.author and str(r.emoji) in ["👍", "👎"]
            )
            bet_higher = str(reaction.emoji) == "👍"
        except asyncio.TimeoutError:
            return await ctx.warn( "Time's up! Bet cancelled.")

        embed.description = f"First roll: **{first_roll}**\nYou bet the next roll will be {'higher' if bet_higher else 'lower'}"
        await msg.edit(embed=embed)
        await asyncio.sleep(1)

        for _ in range(2):
            roll = random.randint(1, 6)
            embed.description = f"First roll: **{first_roll}**\nRolling... **{roll}**!"
            await msg.edit(embed=embed)
            await asyncio.sleep(0.5)

        base_chance = 0.5
        win_chance = min(base_chance * luck_boost, 0.75)
        won = random.random() < win_chance
        final_roll = random.randint(first_roll + 1, 6) if (won and bet_higher) else \
                    random.randint(1, first_roll - 1) if (won and not bet_higher) else \
                    random.randint(1, first_roll - 1) if bet_higher else \
                    random.randint(first_roll + 1, 6)

        if first_roll in [1, 6]: 
            final_roll = random.randint(2, 6) if first_roll == 1 else random.randint(1, 5)
            won = (bet_higher and first_roll == 1) or (not bet_higher and first_roll == 6)

        async with self.bot.db.acquire() as conn:
            async with conn.transaction():
                if won:
                    win_amount = int(amount * win_multiplier)
                    await conn.execute(
                        """UPDATE economy 
                        SET wallet = wallet + $1 
                        WHERE user_id = $2""",
                        win_amount - amount, ctx.author.id
                    )
                    if win_multiplier > 2.0:
                        await self.use_one_time_effect(
                            ctx.author.id, 'next_gamble_multiplier'
                        )
                    await self.log_transaction(ctx.author.id, "gamble_win", win_amount)
                    
                    await self.bot.redis.incr(f"win_streak:{ctx.author.id}")
                    await self.bot.redis.expire(f"win_streak:{ctx.author.id}", 3600)
                else:
                    await conn.execute(
                        """UPDATE economy 
                        SET wallet = wallet - $1 
                        WHERE user_id = $2""",
                        amount, ctx.author.id
                    )
                    await self.log_transaction(ctx.author.id, "gamble_loss", -amount)
                    await self.bot.redis.delete(f"win_streak:{ctx.author.id}")

                await self.bot.redis.incrby(f"daily_gambled:{ctx.author.id}", amount)
                if daily_gambled == 0:
                    await self.bot.redis.expire(f"daily_gambled:{ctx.author.id}", 86400)

        embed.description = (
            f"First roll: **{first_roll}**\n"
            f"Final roll: **{final_roll}**\n\n"
            f"{'🎉 You won' if won else '😢 You lost'} "
            f"**{amount:,}** coins!"
        )
        if won and win_multiplier > 2.0:
            embed.description += f"\n🌟 Multiplier bonus: {win_multiplier}x"

        await msg.edit(embed=embed)

    @gamble.command(name="slots")
    @is_econ_allowed()
    @commands.cooldown(1, 3, BucketType.user)
    async def slots(self, ctx: Context, amount: str):
        """Play the slot machine"""
        if amount.lower() == 'all':
            wallet, _, _ = await self.get_balance(ctx.author.id)
            amount = wallet
        else:
            try:
                amount = int(amount.replace(',', ''))
            except ValueError:
                return await ctx.warn( "Please provide a valid amount or `all`")

        if amount < 100:
            return await ctx.warn( "Minimum bet is 100 coins!")

        daily_gambled = int(await self.bot.redis.get(f"daily_gambled:{ctx.author.id}") or 0)
        daily_limit = 1_000_000
        if daily_gambled + amount > daily_limit:
            remaining = daily_limit - daily_gambled
            return await ctx.warn( 
                f"Daily gambling limit reached! You can only gamble {remaining:,} more coins today."
            )

        house_edge = min(0.05 + (amount / 1_000_000) * 0.15, 0.25)
        base_chance = 0.15 * (1 - house_edge)
        win_chance = min(base_chance * luck_boost, 0.30)

        win_streak = int(await self.bot.redis.get(f"win_streak:{ctx.author.id}") or 0)
        if win_streak > 3:
            win_chance *= 0.8

        wallet, _, _ = await self.get_balance(ctx.author.id)
        if amount > wallet:
            return await ctx.warn( "You don't have enough coins!")

        effects = await self.get_active_effects(ctx.author.id)
        luck_boost = effects.get('gambling_luck', {'value': 1.0})['value']
        win_multiplier = effects.get('next_gamble_multiplier', {'value': 2.0})['value']

        symbols = {
            "🍒": {"weight": 35, "payout": 1.5},   
            "🍊": {"weight": 25, "payout": 2.0},   
            "🍇": {"weight": 20, "payout": 2.5},   
            "🍎": {"weight": 12, "payout": 3.0},  
            "💎": {"weight": 6, "payout": 5.0},    
            "🎰": {"weight": 2, "payout": 10.0},   
        }

        embed = Embed(title="🎰 Slot Machine", color=discord.Color.gold())
        embed.add_field(
            name="Your Bet",
            value=f"**{amount:,}** coins"
        )
        if luck_boost > 1.0:
            embed.add_field(
                name="🍀 Luck Boost",
                value=f"+{(luck_boost-1)*100:.0f}% win chance"
            )

        msg = await ctx.send(embed=embed)

        for _ in range(3):
            slots = [random.choice(list(symbols.keys())) for _ in range(3)]
            embed.description = f"[ {' | '.join(slots)} ]"
            await msg.edit(embed=embed)
            await asyncio.sleep(0.7)

        # CHECKPOINT, % OF WINNING FOR SLOTS    

        base_chance = 0.15
        win_chance = min(base_chance * luck_boost, 0.30)
        won = random.random() < win_chance

        if won:
            symbol = random.choices(
                list(symbols.keys()),
                weights=[s["weight"] for s in symbols.values()]
            )[0]
            final_slots = [symbol] * 3
        else:
            while True:
                final_slots = [
                    random.choices(
                        list(symbols.keys()),
                        weights=[s["weight"] for s in symbols.values()]
                    )[0]
                    for _ in range(3)
                ]
                if not (final_slots[0] == final_slots[1] == final_slots[2]):
                    break

        embed.description = f"[ {' | '.join(final_slots)} ]"

        if won:
            symbol = final_slots[0]
            win_amount = int(amount * symbols[symbol]["payout"] * win_multiplier)
            async with self.bot.db.acquire() as conn:
                async with conn.transaction():
                    await conn.execute(
                        """UPDATE economy 
                        SET wallet = wallet + $1 
                        WHERE user_id = $2""",
                        win_amount - amount, ctx.author.id
                    )
                    if win_multiplier > 2.0:
                        await self.use_one_time_effect(
                            ctx.author.id, 'next_gamble_multiplier'
                        )
                    await self.log_transaction(ctx.author.id, "gamble_win", win_amount)
                    
                    await self.bot.redis.incr(f"win_streak:{ctx.author.id}")
                    await self.bot.redis.expire(f"win_streak:{ctx.author.id}", 3600)
                    
                    await self.bot.redis.incrby(f"daily_gambled:{ctx.author.id}", amount)
                    if daily_gambled == 0:
                        await self.bot.redis.expire(f"daily_gambled:{ctx.author.id}", 86400)
        else:
            async with self.bot.db.acquire() as conn:
                async with conn.transaction():
                    await conn.execute(
                        """UPDATE economy 
                        SET wallet = wallet - $1 
                        WHERE user_id = $2""",
                        amount, ctx.author.id
                    )
                    await self.log_transaction(ctx.author.id, "gamble_loss", -amount)
                    await self.bot.redis.delete(f"win_streak:{ctx.author.id}")
                    
                    await self.bot.redis.incrby(f"daily_gambled:{ctx.author.id}", amount)
                    if daily_gambled == 0:
                        await self.bot.redis.expire(f"daily_gambled:{ctx.author.id}", 86400)

        embed.description += (
            f"\n\n🎉 You won **{win_amount:,}** coins! "
            f"({symbols[symbol]['payout']}x payout)"
        )
        if win_multiplier > 2.0:
            embed.description += f"\n🌟 Multiplier bonus: {win_multiplier}x"

        await msg.edit(embed=embed)

    @gamble.command(name="blackjack", aliases=["bj"])
    @is_econ_allowed()
    @commands.cooldown(1, 3, BucketType.user)
    async def blackjack(self, ctx: Context, amount: str, *, bet_type: str = "coins"):
        """Start a blackjack game"""
        if bet_type.lower() == "coins":
            if amount.lower() == 'all':
                wallet, _, _ = await self.get_balance(ctx.author.id)
                amount = wallet
            else:
                try:
                    amount = int(amount.replace(',', ''))
                except ValueError:
                    return await ctx.warn( "Please provide a valid amount or `all`")

            if amount < 100:
                return await ctx.warn( "Minimum bet is 100 coins!")

            daily_gambled = int(await self.bot.redis.get(f"daily_gambled:{ctx.author.id}") or 0)
            daily_limit = 1_000_000
            if daily_gambled + amount > daily_limit:
                remaining = daily_limit - daily_gambled
                return await ctx.warn( 
                    f"Daily gambling limit reached! You can only gamble {remaining:,} more coins today."
                )

            wallet, _, _ = await self.get_balance(ctx.author.id)
            if amount > wallet:
                return await ctx.warn( "You don't have enough coins!")

            await self.bot.redis.incrby(f"daily_gambled:{ctx.author.id}", amount)
            if daily_gambled == 0:
                await self.bot.redis.expire(f"daily_gambled:{ctx.author.id}", 86400)

        active_games_key = f"active_blackjack_games:{ctx.channel.id}"
        
        if await self.bot.redis.exists(active_games_key):
            return await ctx.warn( "A game is already in progress in this channel!")

        if bet_type.lower().startswith("business:"):
            business_name = bet_type.split(":", 1)[1]
            business = await self.bot.db.fetchrow(
                """SELECT * FROM businesses 
                WHERE owner_id = $1 AND name = $2 AND EXISTS (
                    SELECT 1 FROM businesses WHERE owner_id = $1
                )""",
                ctx.author.id, business_name
            )
            if not business:
                return await ctx.warn( "You don't own this business!")
            bet_value = business["balance"]
            bet_type = {"type": "business", "data": business}
        
        elif bet_type.lower().startswith("item:"):
            item_name = bet_type.split(":", 1)[1]
            item = await self.bot.db.fetchrow(
                """SELECT ui.*, si.* FROM user_items ui
                JOIN shop_items si ON ui.item_id = si.item_id
                WHERE ui.user_id = $1 AND si.name = $2""",
                ctx.author.id, item_name
            )
            if not item or item["quantity"] <= 0:
                return await ctx.warn( "You don't own this item!")
            bet_value = item["price"]
            bet_type = {"type": "item", "data": item}
        
        else:
            if amount.lower() == 'all':
                wallet, _, _ = await self.get_balance(ctx.author.id)
                amount = wallet
            else:
                try:
                    amount = int(amount.replace(',', ''))
                except ValueError:
                    return await ctx.warn( "Please provide a valid amount or `all`")

            if amount < 100:
                return await ctx.warn( "Minimum bet is 100 coins!")

            wallet, _, _ = await self.get_balance(ctx.author.id)
            if amount > wallet:
                return await ctx.warn( "You don't have enough coins!")
            
            bet_value = amount
            bet_type = {"type": "coins", "data": amount}

        game = BlackjackGame(ctx, bet_value, bet_type, self) 
        game.players.append({
            "user": ctx.author,
            "bet": bet_value,
            "bet_type": bet_type,
            "hand": [],
            "insurance": 0,
            "status": "Waiting"
        })

        await self.bot.redis.setex(active_games_key, 300, game.game_id)

        try:
            embed = Embed(
                title="🎰 Blackjack Game",
                description=(
                    f"**Bet:** {bet_value:,} coins\n"
                    "React with 🃏 to join! (30 seconds)\n"
                    "Game will start automatically with dealer if no one joins."
                ),
                color=discord.Color.gold()
            )
            game.game_message = await ctx.send(embed=embed)
            await game.game_message.add_reaction("🃏")

            join_end = time.time() + 30
            while time.time() < join_end and len(game.players) < 4:
                try:
                    reaction, user = await ctx.bot.wait_for(
                        'reaction_add',
                        timeout=join_end - time.time(),
                        check=lambda r, u: (
                            str(r.emoji) == "🃏" and 
                            r.message.id == game.game_message.id and
                            not u.bot and
                            u.id not in [p["user"].id for p in game.players]
                        )
                    )
                    
                    wallet, _, _ = await self.get_balance(user.id)
                    if wallet >= bet_value:
                        game.players.append({
                            "user": user,
                            "bet": bet_value,
                            "bet_type": {"type": "coins", "data": bet_value},
                            "hand": [],
                            "insurance": 0,
                            "status": "Waiting"
                        })
                        await game.update_game_message()
                    else:
                        await ctx.warn( f"{user.mention} doesn't have enough coins!")
                except asyncio.TimeoutError:
                    break

            if len(game.players) == 1:
                await game.start_game()
            else:
                await game.game_message.clear_reactions()
                await game.start_game()

            if game.dealer_hand[0]["value"] == "A":
                await game.offer_insurance()

            while game.game_status == "playing":
                current_player = game.players[game.current_player_index]
                
                action_emojis = {
                    "👊": "hit",
                    "✋": "stand"
                }
                
                if await game.can_double_down(current_player):
                    action_emojis["💰"] = "double"
                if await game.can_split(current_player):
                    action_emojis["✂️"] = "split"

                action_msg = await ctx.send(
                    f"{current_player['user'].mention}'s turn! React to play:\n" +
                    "\n".join(f"{emoji} - {action}" for emoji, action in action_emojis.items())
                )
                
                for emoji in action_emojis:
                    await action_msg.add_reaction(emoji)

                try:
                    reaction, user = await ctx.bot.wait_for(
                        'reaction_add',
                        timeout=30.0,
                        check=lambda r, u: (
                            str(r.emoji) in action_emojis and
                            r.message.id == action_msg.id and
                            u.id == current_player["user"].id
                        )
                    )
                    
                    action = action_emojis[str(reaction.emoji)]
                    await game.handle_action(action)
                    await action_msg.delete()
                    
                except asyncio.TimeoutError:
                    current_player["status"] = "Stand (Time)"
                    await game.next_turn()
                    await action_msg.delete()

        finally:
            await self.bot.redis.delete(active_games_key)

    async def offer_insurance(self):
        """Offer insurance to all players"""
        embed = Embed(
            title="🎰 Insurance Betting",
            description=(
                "Dealer shows an Ace! You can bet insurance.\n"
                "Type `insurance` to place an insurance bet (half your original bet).\n"
                "Insurance pays 2:1 if dealer has blackjack.\n"
                "You have 15 seconds to decide."
            ),
            color=discord.Color.gold()
        )
        await self.ctx.send(embed=embed)

        def check(m):
            return (
                m.channel == self.ctx.channel and
                m.content.lower() == "insurance" and
                any(p["user"].id == m.author.id for p in self.players)
            )

        try:
            while True:
                msg = await self.ctx.bot.wait_for('message', timeout=15.0, check=check)
                player = next(p for p in self.players if p["user"].id == msg.author.id)
                
                if player["insurance"] == 0:
                    insurance_amount = player["bet"] // 2
                    wallet, _, _ = await self.get_balance(player["user"].id)
                    
                    if wallet >= insurance_amount:
                        player["insurance"] = insurance_amount
                        await self.ctx.approve(f"{player['user'].name} placed insurance bet of {insurance_amount:,} coins")
                    else:
                        await self.ctx.warn( f"{player['user'].name} doesn't have enough coins for insurance!")
        except asyncio.TimeoutError:
            pass

        if self.calculate_hand(self.dealer_hand) == 21:
            self.game_status = "ended"
            await self.handle_insurance_payouts()
            await self.end_game()

    async def handle_insurance_payouts(self):
        """Handle insurance bet payouts"""
        async with self.ctx.bot.db.acquire() as conn:
            async with conn.transaction():
                for player in self.players:
                    if player["insurance"] > 0:
                        payout = player["insurance"] * 2
                        await conn.execute(
                            """UPDATE economy 
                            SET wallet = wallet + $1 
                            WHERE user_id = $2""",
                            payout, player["user"].id
                        )
                        player["status"] = f"Insurance Won (+{payout:,})"

    async def get_active_effects(self, user_id: int) -> dict:
        """Get all active effects for a user"""
        effects = {}
        
        active_items = await self.bot.db.fetch(
            """SELECT ui.*, si.effect_type, si.effect_value, si.duration
            FROM user_items ui
            JOIN shop_items si ON ui.item_id = si.item_id
            WHERE ui.user_id = $1 
            AND ui.quantity > 0
            AND (
                ui.expires_at IS NULL 
                OR ui.expires_at > CURRENT_TIMESTAMP
            )""",
            user_id
        )

        for item in active_items:
            effect_type = item['effect_type']
            if effect_type:
                effects[effect_type] = {
                    'value': item['effect_value'],
                    'expires': item['expires_at']
                }

        return effects

    async def use_one_time_effect(self, user_id: int, effect_type: str):
        """Use up a one-time effect item"""
        await self.bot.db.execute(
            """UPDATE user_items ui
            SET quantity = quantity - 1
            FROM shop_items si
            WHERE ui.item_id = si.item_id
            AND ui.user_id = $1
            AND si.effect_type = $2
            AND ui.quantity > 0""",
            user_id, effect_type
        )

    @gamble.command(name="roulette")
    @is_econ_allowed()
    @commands.cooldown(1, 3, BucketType.user)
    async def roulette(self, ctx: Context, bet_type: str, amount: str):
        """
        Play roulette. Bet types:
        red/black: 2x payout
        even/odd: 2x payout
        number (0-36): 35x payout
        dozen (1-12/13-24/25-36): 3x payout
        """
        if amount.lower() == 'all':
            wallet, _, _ = await self.get_balance(ctx.author.id)
            amount = wallet
        else:
            try:
                amount = int(amount.replace(',', ''))
            except ValueError:
                return await ctx.warn( "Please provide a valid amount or `all`")

        if amount < 100:
            return await ctx.warn( "Minimum bet is 100 coins!")

        daily_gambled = int(await self.bot.redis.get(f"daily_gambled:{ctx.author.id}") or 0)
        daily_limit = 1_000_000
        if daily_gambled + amount > daily_limit:
            remaining = daily_limit - daily_gambled
            return await ctx.warn( 
                f"Daily gambling limit reached! You can only gamble {remaining:,} more coins today."
            )

        numbers = {
            0: {"color": "green", "dozen": None, "even": False},
            **{
                n: {
                    "color": "red" if n in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36] else "black",
                    "dozen": "1st" if n <= 12 else "2nd" if n <= 24 else "3rd",
                    "even": n % 2 == 0
                }
                for n in range(1, 37)
            }
        }

        bet_type = bet_type.lower()
        if bet_type in ['red', 'black']:
            multiplier = 2
            valid_numbers = [n for n, props in numbers.items() if props["color"] == bet_type]
        elif bet_type in ['even', 'odd']:
            multiplier = 2
            valid_numbers = [n for n, props in numbers.items() if (n % 2 == 0) == (bet_type == 'even')]
        elif bet_type in ['1st', '2nd', '3rd']:
            multiplier = 3
            valid_numbers = [n for n, props in numbers.items() if props["dozen"] == bet_type]
        else:
            try:
                number = int(bet_type)
                if 0 <= number <= 36:
                    multiplier = 35
                    valid_numbers = [number]
                else:
                    return await ctx.warn( "Invalid number! Choose 0-36")
            except ValueError:
                return await ctx.warn( 
                    "Invalid bet type! Choose:\n"
                    "- red/black\n"
                    "- even/odd\n"
                    "- 1st/2nd/3rd (dozens)\n"
                    "- number (0-36)"
                )

        house_edge = min(0.05 + (amount / 1_000_000) * 0.15, 0.25)
        base_chance = (len(valid_numbers) / 38) * (1 - house_edge)
        
        effects = await self.get_active_effects(ctx.author.id)
        luck_boost = effects.get('gambling_luck', {'value': 1.0})['value']
        win_multiplier = effects.get('next_gamble_multiplier', {'value': multiplier})['value']
        
        win_chance = min(base_chance * luck_boost, 0.60)
        
        win_streak = int(await self.bot.redis.get(f"win_streak:{ctx.author.id}") or 0)
        if win_streak > 3:
            win_chance *= 0.8

        wallet, _, _ = await self.get_balance(ctx.author.id)
        if amount > wallet:
            return await ctx.warn( "You don't have enough coins!")

        embed = Embed(title="🎰 Roulette", color=discord.Color.gold())
        embed.add_field(
            name="Your Bet",
            value=f"**{amount:,}** coins on **{bet_type}**"
        )
        if luck_boost > 1.0:
            embed.add_field(
                name="🍀 Luck Boost",
                value=f"+{(luck_boost-1)*100:.0f}% win chance"
            )

        msg = await ctx.send(embed=embed)

        for _ in range(3):
            number = random.randint(0, 36)
            color = numbers[number]["color"]
            embed.description = f"Spinning... **{number}** {color}!"
            await msg.edit(embed=embed)
            await asyncio.sleep(0.7)

        won = random.random() < win_chance

        if won:
            final_number = random.choice(valid_numbers)
        else:
            invalid_numbers = [n for n in range(37) if n not in valid_numbers]
            final_number = random.choice(invalid_numbers)

        final_color = numbers[final_number]["color"]

        async with self.bot.db.acquire() as conn:
            async with conn.transaction():
                if won:
                    win_amount = int(amount * win_multiplier)
                    await conn.execute(
                        """UPDATE economy 
                        SET wallet = wallet + $1 
                        WHERE user_id = $2""",
                        win_amount - amount, ctx.author.id
                    )
                    if win_multiplier > 2.0:
                        await self.use_one_time_effect(
                            ctx.author.id, 'next_gamble_multiplier'
                        )
                    await self.log_transaction(ctx.author.id, "gamble_win", win_amount)
                    
                    await self.bot.redis.incr(f"win_streak:{ctx.author.id}")
                    await self.bot.redis.expire(f"win_streak:{ctx.author.id}", 3600)
                else:
                    await conn.execute(
                        """UPDATE economy 
                        SET wallet = wallet - $1 
                        WHERE user_id = $2""",
                        amount, ctx.author.id
                    )
                    await self.log_transaction(ctx.author.id, "gamble_loss", -amount)
                    await self.bot.redis.delete(f"win_streak:{ctx.author.id}")

        embed.description = (
            f"Ball landed on **{final_number}** {final_color}!\n\n"
            f"{'🎉 You won' if won else '😢 You lost'} "
            f"**{amount:,}** coins!"
        )
        if won and win_multiplier > 2.0:
            embed.description += f"\n🌟 Multiplier bonus: {win_multiplier}x"

        await msg.edit(embed=embed)

    @gamble.command(name="crash")
    @is_econ_allowed()
    @commands.cooldown(1, 3, BucketType.user)
    async def crash(self, ctx: Context, amount: str):
        """
        Multiplier increases until crash. Cash out before it crashes!
        Click the button to cash out.
        Maximum payout: 20,000 coins
        """
        if amount.lower() == "all":
            wallet, _, _ = await self.get_balance(ctx.author.id)
            amount = wallet
        else:
            try:
                amount = int(amount.replace(",", ""))
            except ValueError:
                return await ctx.warn("Please provide a valid amount or `all`")

        if amount < 100:
            return await ctx.warn("Minimum bet is 100 coins!")

        daily_gambled = int(await self.bot.redis.get(f"daily_gambled:{ctx.author.id}") or 0)
        daily_limit = 1_000_000
        if daily_gambled + amount > daily_limit:
            remaining = daily_limit - daily_gambled
            return await ctx.warn(
                f"Daily gambling limit reached! You can only gamble {remaining:,} more coins today."
            )

        effects = await self.get_active_effects(ctx.author.id)
        luck_boost = effects.get("gambling_luck", {"value": 1.0})["value"]
        win_multiplier = effects.get("next_gamble_multiplier", {"value": 1.0})["value"]

        win_streak = int(await self.bot.redis.get(f"win_streak:{ctx.author.id}") or 0)
        base_crash = random.uniform(1.0, 3.5)
        if win_streak > 3:
            base_crash *= 0.8

        crash_point = min(base_crash * luck_boost, 10.0)
        
        base_crash_chance = 0.05 + (amount / 1_000_000) * 0.15

        wallet, _, _ = await self.get_balance(ctx.author.id)
        if amount > wallet:
            return await ctx.warn("You don't have enough coins!")

        class CrashView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=None)
                self.cashed_out = False
                
            @discord.ui.button(label="Cash Out 💰", style=discord.ButtonStyle.green)
            async def cash_out(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user.id != ctx.author.id:
                    return await interaction.response.send_message("This isn't your game!", ephemeral=True)
                self.cashed_out = True
                self.stop()
                await interaction.response.defer()

        view = CrashView()
        embed = Embed(title="📈 Crash Game", color=discord.Color.gold())
        embed.add_field(
            name="Your Bet",
            value=f"**{amount:,}** coins"
        )
        if luck_boost > 1.0:
            embed.add_field(
                name="🍀 Luck Boost",
                value=f"+{(luck_boost-1)*100:.0f}% crash point"
            )

        msg = await ctx.send(embed=embed, view=view)

        multiplier = 1.0
        crash_chance = 0.05
        
        while multiplier < crash_point and not view.cashed_out:
            current_crash_chance = crash_chance * (multiplier ** 1.2)
            if random.random() < current_crash_chance:
                break
                
            embed.description = (
                f"📈 Multiplier: **{multiplier:.2f}x**\n"
                "Click the button to cash out!"
            )
            await msg.edit(embed=embed)
            await asyncio.sleep(0.5)
            multiplier += 0.2

        final_multiplier = multiplier * win_multiplier if view.cashed_out else 0

        view.children[0].disabled = True
        await msg.edit(view=view)

        async with self.bot.db.acquire() as conn:
            async with conn.transaction():
                if view.cashed_out:
                    if multiplier >= 1.0:
                        win_amount = min(int(amount * final_multiplier), 20000)
                        if win_amount < amount:  
                            win_amount = amount
                    else:
                        win_amount = int(amount * final_multiplier)
                        
                    await conn.execute(
                        """UPDATE economy 
                        SET wallet = wallet + $1 
                        WHERE user_id = $2""",
                        win_amount - amount, ctx.author.id
                    )
                    if win_multiplier > 1.0:
                        await self.use_one_time_effect(
                            ctx.author.id, "next_gamble_multiplier"
                        )
                    await self.log_transaction(ctx.author.id, "gamble_win", win_amount)
                    
                    await self.bot.redis.incr(f"win_streak:{ctx.author.id}")
                    await self.bot.redis.expire(f"win_streak:{ctx.author.id}", 3600)
                else:
                    await conn.execute(
                        """UPDATE economy 
                        SET wallet = wallet - $1 
                        WHERE user_id = $2""",
                        amount, ctx.author.id
                    )
                    await self.log_transaction(ctx.author.id, "gamble_loss", -amount)
                    await self.bot.redis.delete(f"win_streak:{ctx.author.id}")

                await self.bot.redis.incrby(f"daily_gambled:{ctx.author.id}", amount)
                if daily_gambled == 0:
                    await self.bot.redis.expire(f"daily_gambled:{ctx.author.id}", 86400)

        if view.cashed_out:
            embed.description = (
                f"💰 Cashed out at **{multiplier:.2f}x**!\n"
                f"You won **{win_amount:,}** coins!"
            )
            if win_amount == 20000:
                embed.description += "\n⚠️ Maximum payout reached!"
            if win_multiplier > 1.0:
                embed.description += f"\n🌟 Multiplier bonus: {win_multiplier}x"
        else:
            embed.description = (
                f"💥 Crashed at **{crash_point:.2f}x**!\n"
                f"You lost **{amount:,}** coins!"
            )

        embed.color = discord.Color.green() if view.cashed_out else discord.Color.red()
        await msg.edit(embed=embed)

    @gamble.command(name="wheel")
    @is_econ_allowed()
    @commands.cooldown(1, 3, BucketType.user)
    async def wheel(self, ctx: Context, amount: str):
        """
        Spin the wheel of fortune!
        Different segments with different multipliers:
        - 0.5x (loss)
        - 1x (money back)
        - 2x
        - 3x
        - 5x
        - 10x (rare)
        """
        if amount.lower() == 'all':
            wallet, _, _ = await self.get_balance(ctx.author.id)
            amount = wallet
        else:
            try:
                amount = int(amount.replace(',', ''))
            except ValueError:
                return await ctx.warn( "Please provide a valid amount or `all`")

        if amount < 100:
            return await ctx.warn( "Minimum bet is 100 coins!")

        wallet, _, _ = await self.get_balance(ctx.author.id)
        if amount > wallet:
            return await ctx.warn( "You don't have enough coins!")

        effects = await self.get_active_effects(ctx.author.id)
        luck_boost = effects.get('gambling_luck', {'value': 1.0})['value']
        win_multiplier = effects.get('next_gamble_multiplier', {'value': 1.0})['value']

        # CHECKPOINT, % WEIGHT OF WHEEL SEGMENTS    

        segments = [
            {"multiplier": 0.0, "weight": 30, "emoji": "💀"},   
            {"multiplier": 0.5, "weight": 25, "emoji": "😢"},  
            {"multiplier": 1.0, "weight": 20, "emoji": "🔄"},  
            {"multiplier": 2.0, "weight": 15, "emoji": "💰"},   
            {"multiplier": 3.0, "weight": 8, "emoji": "🎉"},   
            {"multiplier": 5.0, "weight": 2, "emoji": "💎"},    
        ]

        embed = Embed(title="🎡 Wheel of Fortune", color=discord.Color.gold())
        embed.add_field(
            name="Your Bet",
            value=f"**{amount:,}** coins"
        )
        if luck_boost > 1.0:
            embed.add_field(
                name="🍀 Luck Boost",
                value=f"+{(luck_boost-1)*100:.0f}% better odds"
            )

        msg = await ctx.send(embed=embed)

        for _ in range(3):
            segment = random.choice(segments)
            embed.description = (
                f"Spinning... {segment['emoji']}\n"
                f"Multiplier: **{segment['multiplier']}x**"
            )
            await msg.edit(embed=embed)
            await asyncio.sleep(0.7)

        boosted_segments = segments.copy()
        for segment in boosted_segments:
            if segment["multiplier"] > 1.0:
                segment["weight"] *= luck_boost

        final_segment = random.choices(
            boosted_segments,
            weights=[s["weight"] for s in boosted_segments]
        )[0]

        final_multiplier = final_segment["multiplier"] * win_multiplier

        async with self.bot.db.acquire() as conn:
            async with conn.transaction():
                win_amount = int(amount * final_multiplier)
                if win_amount > amount:  
                    await conn.execute(
                        """UPDATE economy 
                        SET wallet = wallet + $1 
                        WHERE user_id = $2""",
                        win_amount - amount, ctx.author.id
                    )
                    if win_multiplier > 1.0:
                        await self.use_one_time_effect(
                            ctx.author.id, 'next_gamble_multiplier'
                        )
                elif win_amount < amount:  
                    await conn.execute(
                        """UPDATE economy 
                        SET wallet = wallet - $1 
                        WHERE user_id = $2""",
                        amount - win_amount, ctx.author.id
                    )

        embed.description = (
            f"Landed on: {final_segment['emoji']}\n"
            f"Multiplier: **{final_segment['multiplier']}x**\n\n"
        )

        if final_multiplier > final_segment["multiplier"]:
            embed.description += f"🌟 Bonus multiplier: {win_multiplier}x\n\n"

        if win_amount > amount:
            embed.description += f"🎉 You won **{win_amount:,}** coins!"
            embed.color = discord.Color.green()
        elif win_amount < amount:
            embed.description += f"😢 You lost **{amount - win_amount:,}** coins!"
            embed.color = discord.Color.red()
        else:
            embed.description += "🔄 You got your money back!"
            embed.color = config.COLORS.NEUTRAL

        await msg.edit(embed=embed)

    @gamble.command(name="ladder")
    @is_econ_allowed()
    @commands.cooldown(1, 3, BucketType.user)
    async def ladder_climb(self, ctx: Context, amount: str):
        """
        Climb the money ladder! Each step up doubles your bet.
        Choose when to cash out, but fall and lose everything!
        Max 5 steps: 2x -> 4x -> 8x -> 16x -> 32x
        Chance to fall increases with each step
        """
        if amount.lower() == 'all':
            wallet, _, _ = await self.get_balance(ctx.author.id)
            amount = wallet
        else:
            try:
                amount = int(amount.replace(',', ''))
            except ValueError:
                return await ctx.warn("Please provide a valid amount or `all`")

        if amount < 100:
            return await ctx.warn("Minimum bet is 100 coins!")

        daily_gambled = int(await self.bot.redis.get(f"daily_gambled:{ctx.author.id}") or 0)
        daily_limit = 1_000_000
        if daily_gambled + amount > daily_limit:
            remaining = daily_limit - daily_gambled
            return await ctx.warn(
                f"Daily gambling limit reached! You can only gamble {remaining:,} more coins today."
            )

        wallet, _, _ = await self.get_balance(ctx.author.id)
        if amount > wallet:
            return await ctx.warn("You don't have enough coins!")

        effects = await self.get_active_effects(ctx.author.id)
        luck_boost = effects.get('gambling_luck', {'value': 1.0})['value']
        win_multiplier = effects.get('next_gamble_multiplier', {'value': 1.0})['value']

        class LadderView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=30.0)
                self.value = None
                self.current_step = 0
                self.multiplier = 1
                
            @discord.ui.button(label="Climb 🪜", style=discord.ButtonStyle.green)
            async def climb(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user.id != ctx.author.id:
                    return await interaction.response.send_message(
                        "This isn't your game!", ephemeral=True
                    )
                self.current_step += 1
                self.multiplier *= 2
                self.value = "climb"
                self.stop()
                await interaction.response.defer()

            @discord.ui.button(label="Cash Out 💰", style=discord.ButtonStyle.primary) 
            async def cash_out(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user.id != ctx.author.id:
                    return await interaction.response.send_message(
                        "This isn't your game!", ephemeral=True
                    )
                self.value = "cashout"
                self.stop()
                await interaction.response.defer()

        embed = Embed(title="🪜 Money Ladder", color=discord.Color.gold())
        embed.add_field(
            name="Your Bet",
            value=f"**{amount:,}** coins"
        )
        if luck_boost > 1.0:
            embed.add_field(
                name="🍀 Luck Boost",
                value=f"+{(luck_boost-1)*100:.0f}% climb chance"
            )

        msg = await ctx.send(embed=embed)
        current_step = 0
        current_multiplier = 1
        game_active = True

        while game_active and current_step < 5:
            view = LadderView()
            view.current_step = current_step
            view.multiplier = current_multiplier

            steps_display = []
            for step in range(5):
                multiplier = 2 ** (step + 1)
                if step < current_step:
                    steps_display.append(f"✅ {multiplier}x")
                elif step == current_step:
                    steps_display.append(f"👉 {multiplier}x")
                else:
                    steps_display.append(f"⬜ {multiplier}x")

            embed.description = (
                "🪜 **Money Ladder**\n"
                + "\n".join(reversed(steps_display))
                + f"\n\nCurrent multiplier: **{current_multiplier}x**\n"
                f"Potential next win: **{amount * current_multiplier * 2:,}** coins\n"
                "\nClimb higher or cash out?"
            )
            
            await msg.edit(embed=embed, view=view)

            win_streak = int(await self.bot.redis.get(f"win_streak:{ctx.author.id}") or 0)
            if win_streak > 3:
                base_fall_chance *= 1.2            
            try:
                await view.wait()
            except TimeoutError:
                view.value = "timeout"

            if view.value == "climb":
                base_fall_chance = 0.4 + (current_step * 0.2)
                fall_chance = max(0.2, base_fall_chance * (1 / (1 + (luck_boost - 1) * 0.5)))
                
                if random.random() < fall_chance:
                    game_active = False
                    current_multiplier = 0
                else:
                    current_step += 1
                    current_multiplier *= 2
            else:
                game_active = False

        view.children[0].disabled = True
        view.children[1].disabled = True
        await msg.edit(view=view)

        win_amount = int(amount * current_multiplier * win_multiplier)
        
        async with self.bot.db.acquire() as conn:
            async with conn.transaction():
                if win_amount > 0:
                    await conn.execute(
                        """UPDATE economy 
                        SET wallet = wallet + $1 
                        WHERE user_id = $2""",
                        win_amount - amount, ctx.author.id
                    )
                    if win_multiplier > 1.0:
                        await self.use_one_time_effect(
                            ctx.author.id, 'next_gamble_multiplier'
                        )
                    await self.log_transaction(ctx.author.id, "gamble_win", win_amount)
                else:
                    await conn.execute(
                        """UPDATE economy 
                        SET wallet = wallet - $1 
                        WHERE user_id = $2""",
                        amount, ctx.author.id
                    )
                    await self.log_transaction(ctx.author.id, "gamble_loss", -amount)

                await self.bot.redis.incrby(f"daily_gambled:{ctx.author.id}", amount)
                if daily_gambled == 0:
                    await self.bot.redis.expire(f"daily_gambled:{ctx.author.id}", 86400)

        if view.value == "timeout":
            embed.description = "Game ended due to inactivity!"
        elif current_multiplier == 0:
            embed.description = "💥 You fell off the ladder and lost everything!"
        else:
            embed.description = (
                f"🎉 Cashed out at **{current_multiplier}x**!\n"
                f"You won **{win_amount:,}** coins!"
            )
            if win_multiplier > 1.0:
                embed.description += f"\n🌟 Bonus multiplier: {win_multiplier}x"

        embed.color = discord.Color.green() if win_amount > 0 else discord.Color.red()
        await msg.edit(embed=embed)

    @gamble.command(name="race")
    @is_econ_allowed()
    @commands.cooldown(1, 3, BucketType.user)
    async def horse_race(self, ctx: Context, horse: int, amount: str):
        """
        Bet on 1 of 5 horses in a race
        Different odds for each horse:
        1: 1.5x (favorite)
        2: 2x
        3: 3x
        4: 5x
        5: 10x (underdog)
        """
        if not 1 <= horse <= 5:
            return await ctx.warn("Please choose a horse number between 1 and 5!")

        if amount.lower() == 'all':
            wallet, _, _ = await self.get_balance(ctx.author.id)
            amount = wallet
        else:
            try:
                amount = int(amount.replace(',', ''))
            except ValueError:
                return await ctx.warn("Please provide a valid amount or `all`")

        if amount < 100:
            return await ctx.warn("Minimum bet is 100 coins!")

        daily_gambled = int(await self.bot.redis.get(f"daily_gambled:{ctx.author.id}") or 0)
        daily_limit = 1_000_000
        if daily_gambled + amount > daily_limit:
            remaining = daily_limit - daily_gambled
            return await ctx.warn(
                f"Daily gambling limit reached! You can only gamble {remaining:,} more coins today."
            )

        wallet, _, _ = await self.get_balance(ctx.author.id)
        if amount > wallet:
            return await ctx.warn("You don't have enough coins!")

        effects = await self.get_active_effects(ctx.author.id)
        luck_boost = effects.get('gambling_luck', {'value': 1.0})['value']
        win_multiplier = effects.get('next_gamble_multiplier', {'value': 1.0})['value']

        horses = {
            1: {"name": "Shadow", "multiplier": 1.5, "emoji": "🏇"},
            2: {"name": "Thunder", "multiplier": 2.0, "emoji": "🐎"},
            3: {"name": "Storm", "multiplier": 3.0, "emoji": "🏇"},
            4: {"name": "Lightning", "multiplier": 5.0, "emoji": "🐎"},
            5: {"name": "Spirit", "multiplier": 10.0, "emoji": "🏇"}
        }

        selected_horse = horses[horse]
        track_length = 12
        positions = {i: 0 for i in range(1, 6)}

        embed = Embed(title="🏇 Horse Race", color=discord.Color.gold())
        embed.add_field(
            name="Your Bet",
            value=(
                f"**{amount:,}** coins on "
                f"**{selected_horse['name']}** (#{horse})\n"
                f"Potential win: **{int(amount * selected_horse['multiplier']):,}** coins"
            )
        )
        if luck_boost > 1.0:
            embed.add_field(
                name="🍀 Luck Boost",
                value=f"+{(luck_boost-1)*100:.0f}% win chance"
            )

        msg = await ctx.send(embed=embed)

        winner = None
        while not winner:
            track_display = []
            for h in range(1, 6):
                base_speed = random.randint(1, 3) * (1.2 - (h * 0.1))
                
                if h == horse:
                    base_speed *= (1 + (luck_boost - 1) * 0.3)
                
                positions[h] += base_speed
                
                track = "." * track_length
                pos = min(int(positions[h]), track_length - 1)
                track = track[:pos] + horses[h]["emoji"] + track[pos + 1:]
                
                track += "🏁"
                track_display.append(f"`{h}` {horses[h]['name']}: {track}")

                if positions[h] >= track_length:
                    winner = h
                    break

            embed.description = "\n".join(track_display)
            await msg.edit(embed=embed)
            await asyncio.sleep(1)

        won = winner == horse
        if won:
            win_amount = int(amount * selected_horse['multiplier'] * win_multiplier)
        else:
            win_amount = 0
            winning_horse = horses[winner]
            embed.description += f"\n\n🏆 **{winning_horse['name']}** wins!"

        async with self.bot.db.acquire() as conn:
            async with conn.transaction():
                if won:
                    await conn.execute(
                        """UPDATE economy 
                        SET wallet = wallet + $1 
                        WHERE user_id = $2""",
                        win_amount - amount, ctx.author.id
                    )
                    if win_multiplier > 1.0:
                        await self.use_one_time_effect(
                            ctx.author.id, 'next_gamble_multiplier'
                        )
                    await self.log_transaction(ctx.author.id, "gamble_win", win_amount)
                    
                    await self.bot.redis.incr(f"win_streak:{ctx.author.id}")
                    await self.bot.redis.expire(f"win_streak:{ctx.author.id}", 3600)
                else:
                    await conn.execute(
                        """UPDATE economy 
                        SET wallet = wallet - $1 
                        WHERE user_id = $2""",
                        amount, ctx.author.id
                    )
                    await self.log_transaction(ctx.author.id, "gamble_loss", -amount)
                    await self.bot.redis.delete(f"win_streak:{ctx.author.id}")

                await self.bot.redis.incrby(f"daily_gambled:{ctx.author.id}", amount)
                if daily_gambled == 0:
                    await self.bot.redis.expire(f"daily_gambled:{ctx.author.id}", 86400)

        if won:
            embed.description += (
                f"\n\n🎉 Your horse won! You got **{win_amount:,}** coins!"
            )
            if win_multiplier > 1.0:
                embed.description += f"\n🌟 Bonus multiplier: {win_multiplier}x"
        else:
            embed.description += f"\n\n😢 You lost **{amount:,}** coins!"

        embed.color = discord.Color.green() if won else discord.Color.red()
        await msg.edit(embed=embed)

    @gamble.command(name="overunder", aliases=["ou"])
    @is_econ_allowed()
    @commands.cooldown(1, 3, BucketType.user)
    async def over_under(self, ctx: Context, choice: str, amount: str):
        """
        Guess if sum of 2 dice will be over/under 7
        Over 7 (2x)
        Under 7 (2x)
        Exactly 7 (4x)
        """
        choice = choice.lower()
        if choice not in ['over', 'under', '7', 'seven']:
            return await ctx.warn("Please choose `over`, `under`, or `7`!")

        if amount.lower() == 'all':
            wallet, _, _ = await self.get_balance(ctx.author.id)
            amount = wallet
        else:
            try:
                amount = int(amount.replace(',', ''))
            except ValueError:
                return await ctx.warn("Please provide a valid amount or `all`")

        if amount < 100:
            return await ctx.warn("Minimum bet is 100 coins!")

        daily_gambled = int(await self.bot.redis.get(f"daily_gambled:{ctx.author.id}") or 0)
        daily_limit = 1_000_000
        if daily_gambled + amount > daily_limit:
            remaining = daily_limit - daily_gambled
            return await ctx.warn(
                f"Daily gambling limit reached! You can only gamble {remaining:,} more coins today."
            )

        wallet, _, _ = await self.get_balance(ctx.author.id)
        if amount > wallet:
            return await ctx.warn("You don't have enough coins!")

        effects = await self.get_active_effects(ctx.author.id)
        luck_boost = effects.get('gambling_luck', {'value': 1.0})['value']
        win_multiplier = effects.get('next_gamble_multiplier', {'value': 1.0})['value']

        embed = Embed(title="🎲 Over/Under 7", color=discord.Color.gold())
        embed.add_field(
            name="Your Bet",
            value=f"**{amount:,}** coins on **{choice}**"
        )
        if luck_boost > 1.0:
            embed.add_field(
                name="🍀 Luck Boost",
                value=f"+{(luck_boost-1)*100:.0f}% win chance"
            )

        msg = await ctx.send(embed=embed)

        dice_faces = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
        for _ in range(3):
            rolls = [random.choice(dice_faces) for _ in range(2)]
            embed.description = f"Rolling... **{' '.join(rolls)}**"
            await msg.edit(embed=embed)
            await asyncio.sleep(0.7)

        dice1 = random.randint(1, 6)
        dice2 = random.randint(1, 6)
        total = dice1 + dice2

        if choice in ['7', 'seven']:
            won = total == 7
            multiplier = 4
        elif choice == 'over':
            won = total > 7
            multiplier = 2
        else:  
            won = total < 7
            multiplier = 2

        base_chance = 0.5
        win_chance = min(base_chance * luck_boost, 0.75)
        won = won and random.random() < win_chance

        async with self.bot.db.acquire() as conn:
            async with conn.transaction():
                if won:
                    win_amount = int(amount * multiplier * win_multiplier)
                    await conn.execute(
                        """UPDATE economy 
                        SET wallet = wallet + $1 
                        WHERE user_id = $2""",
                        win_amount - amount, ctx.author.id
                    )
                    if win_multiplier > 1.0:
                        await self.use_one_time_effect(
                            ctx.author.id, 'next_gamble_multiplier'
                        )
                    await self.log_transaction(ctx.author.id, "gamble_win", win_amount)
                else:
                    await conn.execute(
                        """UPDATE economy 
                        SET wallet = wallet - $1 
                        WHERE user_id = $2""",
                        amount, ctx.author.id
                    )
                    await self.log_transaction(ctx.author.id, "gamble_loss", -amount)

                await self.bot.redis.incrby(f"daily_gambled:{ctx.author.id}", amount)
                if daily_gambled == 0:
                    await self.bot.redis.expire(f"daily_gambled:{ctx.author.id}", 86400)

        dice_str = f"{dice_faces[dice1-1]} {dice_faces[dice2-1]}"
        embed.description = (
            f"Rolled: **{dice_str}**\n"
            f"Total: **{total}**\n\n"
            f"{'🎉 You won' if won else '😢 You lost'} "
            f"**{amount:,}** coins!"
        )
        if won:
            embed.description += f"\n💫 {multiplier}x multiplier"
            if win_multiplier > 1.0:
                embed.description += f"\n🌟 Bonus multiplier: {win_multiplier}x"

        embed.color = discord.Color.green() if won else discord.Color.red()
        await msg.edit(embed=embed)

    @gamble.command(name="scratch")
    @is_econ_allowed()
    @commands.cooldown(1, 30, BucketType.user)
    async def scratch_card(self, ctx: Context, amount: str):
        """
        Buy a scratch card with 9 covered squares
        Match 3 symbols to win:
        - 💎 (10x)
        - 💰 (5x)
        - 🎲 (3x)
        - 🎯 (2x)
        """
        if amount.lower() == 'all':
            wallet, _, _ = await self.get_balance(ctx.author.id)
            amount = wallet
        else:
            try:
                amount = int(amount.replace(',', ''))
            except ValueError:
                return await ctx.warn("Please provide a valid amount or `all`")

        if amount < 100:
            return await ctx.warn("Minimum bet is 100 coins!")

        daily_gambled = int(await self.bot.redis.get(f"daily_gambled:{ctx.author.id}") or 0)
        daily_limit = 1_000_000
        if daily_gambled + amount > daily_limit:
            remaining = daily_limit - daily_gambled
            return await ctx.warn(
                f"Daily gambling limit reached! You can only gamble {remaining:,} more coins today."
            )

        wallet, _, _ = await self.get_balance(ctx.author.id)
        if amount > wallet:
            return await ctx.warn("You don't have enough coins!")

        effects = await self.get_active_effects(ctx.author.id)
        luck_boost = effects.get('gambling_luck', {'value': 1.0})['value']
        win_multiplier = effects.get('next_gamble_multiplier', {'value': 1.0})['value']

        symbols = {
            "💎": {"multiplier": 10, "weight": 1},
            "💰": {"multiplier": 5, "weight": 2},
            "🎲": {"multiplier": 3, "weight": 3},
            "🎯": {"multiplier": 2, "weight": 4},
            "❌": {"multiplier": 0, "weight": 5}
        }

        card = []
        for _ in range(9):
            weights = [s["weight"] for s in symbols.values()]
            symbol = random.choices(list(symbols.keys()), weights=weights)[0]
            card.append({"symbol": symbol, "revealed": False})

        class ScratchView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60.0)
                self.revealed = 0
                self.value = None

            @discord.ui.button(label="1", style=discord.ButtonStyle.gray)
            async def button_1(self, interaction: discord.Interaction, button: discord.ui.Button):
                await self.reveal_square(0, interaction, button)

            @discord.ui.button(label="2", style=discord.ButtonStyle.gray)
            async def button_2(self, interaction: discord.Interaction, button: discord.ui.Button):
                await self.reveal_square(1, interaction, button)

            @discord.ui.button(label="3", style=discord.ButtonStyle.gray)
            async def button_3(self, interaction: discord.Interaction, button: discord.ui.Button):
                await self.reveal_square(2, interaction, button)

            @discord.ui.button(label="4", style=discord.ButtonStyle.gray)
            async def button_4(self, interaction: discord.Interaction, button: discord.ui.Button):
                await self.reveal_square(3, interaction, button)

            @discord.ui.button(label="5", style=discord.ButtonStyle.gray)
            async def button_5(self, interaction: discord.Interaction, button: discord.ui.Button):
                await self.reveal_square(4, interaction, button)

            @discord.ui.button(label="6", style=discord.ButtonStyle.gray)
            async def button_6(self, interaction: discord.Interaction, button: discord.ui.Button):
                await self.reveal_square(5, interaction, button)

            @discord.ui.button(label="7", style=discord.ButtonStyle.gray)
            async def button_7(self, interaction: discord.Interaction, button: discord.ui.Button):
                await self.reveal_square(6, interaction, button)

            @discord.ui.button(label="8", style=discord.ButtonStyle.gray)
            async def button_8(self, interaction: discord.Interaction, button: discord.ui.Button):
                await self.reveal_square(7, interaction, button)

            @discord.ui.button(label="9", style=discord.ButtonStyle.gray)
            async def button_9(self, interaction: discord.Interaction, button: discord.ui.Button):
                await self.reveal_square(8, interaction, button)

            async def reveal_square(self, index: int, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user.id != ctx.author.id:
                    return await interaction.response.send_message(
                        "This isn't your game!", ephemeral=True
                    )
                
                if card[index]["revealed"]:
                    return await interaction.response.send_message(
                        "This square is already revealed!", ephemeral=True
                    )

                card[index]["revealed"] = True
                button.label = card[index]["symbol"]
                button.disabled = True
                self.revealed += 1

                if self.revealed >= 6:
                    self.value = "done"
                    self.stop()

                await interaction.response.edit_message(view=self)

        embed = Embed(
            title="🎟️ Scratch Card",
            description=(
                "Reveal squares to find matching symbols!\n"
                "Match 3 to win:\n"
                "💎 = 10x\n"
                "💰 = 5x\n"
                "🎲 = 3x\n"
                "🎯 = 2x\n"
                "❌ = Loss"
            ),
            color=discord.Color.gold()
        )
        embed.add_field(
            name="Your Bet",
            value=f"**{amount:,}** coins"
        )

        view = ScratchView()
        msg = await ctx.send(embed=embed, view=view)

        try:
            await view.wait()
        except TimeoutError:
            view.value = "timeout"

        for button in view.children:
            button.disabled = True

        for i, button in enumerate(view.children):
            button.label = card[i]["symbol"]

        await msg.edit(view=view)

        symbol_counts = {}
        for square in card:
            symbol = square["symbol"]
            symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1

        winning_symbol = None
        for symbol, count in symbol_counts.items():
            if count >= 3:
                winning_symbol = symbol
                break

        if winning_symbol:
            multiplier = symbols[winning_symbol]["multiplier"]
            win_amount = int(amount * multiplier * win_multiplier)
        else:
            win_amount = 0

        async with self.bot.db.acquire() as conn:
            async with conn.transaction():
                if win_amount > 0:
                    await conn.execute(
                        """UPDATE economy 
                        SET wallet = wallet + $1 
                        WHERE user_id = $2""",
                        win_amount - amount, ctx.author.id
                    )
                    if win_multiplier > 1.0:
                        await self.use_one_time_effect(
                            ctx.author.id, 'next_gamble_multiplier'
                        )
                    await self.log_transaction(ctx.author.id, "gamble_win", win_amount)
                else:
                    await conn.execute(
                        """UPDATE economy 
                        SET wallet = wallet - $1 
                        WHERE user_id = $2""",
                        amount, ctx.author.id
                    )
                    await self.log_transaction(ctx.author.id, "gamble_loss", -amount)

                await self.bot.redis.incrby(f"daily_gambled:{ctx.author.id}", amount)
                if daily_gambled == 0:
                    await self.bot.redis.expire(f"daily_gambled:{ctx.author.id}", 86400)

        if view.value == "timeout":
            embed.description = "Game ended due to inactivity!"
        elif win_amount > 0:
            embed.description = (
                f"🎉 Matched 3 {winning_symbol}!\n"
                f"You won **{win_amount:,}** coins!"
            )
            if win_multiplier > 1.0:
                embed.description += f"\n🌟 Bonus multiplier: {win_multiplier}x"
        else:
            embed.description = f"😢 No matches! You lost **{amount:,}** coins!"

        embed.color = discord.Color.green() if win_amount > 0 else discord.Color.red()
        await msg.edit(embed=embed)

    @gamble.command(name="poker")
    @is_econ_allowed()
    @commands.cooldown(1, 3, BucketType.user)
    async def poker_dice(self, ctx: Context, amount: str):
        """
        Roll 5 dice and win based on poker hands:
        - Five of a kind (50x)
        - Four of a kind (20x)
        - Full house (10x)
        - Three of a kind (5x)
        - Two pair (3x)
        - One pair (2x)
        """
        if amount.lower() == 'all':
            wallet, _, _ = await self.get_balance(ctx.author.id)
            amount = wallet
        else:
            try:
                amount = int(amount.replace(',', ''))
            except ValueError:
                return await ctx.warn("Please provide a valid amount or `all`")

        if amount < 100:
            return await ctx.warn("Minimum bet is 100 coins!")

        daily_gambled = int(await self.bot.redis.get(f"daily_gambled:{ctx.author.id}") or 0)
        daily_limit = 1_000_000
        if daily_gambled + amount > daily_limit:
            remaining = daily_limit - daily_gambled
            return await ctx.warn(
                f"Daily gambling limit reached! You can only gamble {remaining:,} more coins today."
            )

        wallet, _, _ = await self.get_balance(ctx.author.id)
        if amount > wallet:
            return await ctx.warn("You don't have enough coins!")

        effects = await self.get_active_effects(ctx.author.id)
        luck_boost = effects.get('gambling_luck', {'value': 1.0})['value']
        win_multiplier = effects.get('next_gamble_multiplier', {'value': 1.0})['value']

        embed = Embed(title="🎲 Poker Dice", color=discord.Color.gold())
        embed.add_field(
            name="Your Bet",
            value=f"**{amount:,}** coins"
        )
        if luck_boost > 1.0:
            embed.add_field(
                name="🍀 Luck Boost",
                value=f"+{(luck_boost-1)*100:.0f}% better odds"
            )

        msg = await ctx.send(embed=embed)

        dice_faces = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
        for _ in range(3):
            rolls = [random.choice(dice_faces) for _ in range(5)]
            embed.description = f"Rolling... **{' '.join(rolls)}**"
            await msg.edit(embed=embed)
            await asyncio.sleep(0.7)

        rolls = [random.randint(1, 6) for _ in range(5)]
        counts = {x: rolls.count(x) for x in set(rolls)}
        
        if 5 in counts.values():
            hand = "Five of a kind"
            multiplier = 50
        elif 4 in counts.values():
            hand = "Four of a kind"
            multiplier = 20
        elif 3 in counts.values() and 2 in counts.values():
            hand = "Full house"
            multiplier = 10
        elif 3 in counts.values():
            hand = "Three of a kind"
            multiplier = 5
        elif list(counts.values()).count(2) == 2:
            hand = "Two pair"
            multiplier = 3
        elif 2 in counts.values():
            hand = "One pair"
            multiplier = 2
        else:
            hand = "High card"
            multiplier = 0

        base_chance = 0.5
        win_chance = min(base_chance * luck_boost, 0.75)
        won = multiplier > 0 and random.random() < win_chance

        async with self.bot.db.acquire() as conn:
            async with conn.transaction():
                if won:
                    win_amount = int(amount * multiplier * win_multiplier)
                    await conn.execute(
                        """UPDATE economy 
                        SET wallet = wallet + $1 
                        WHERE user_id = $2""",
                        win_amount - amount, ctx.author.id
                    )
                    if win_multiplier > 1.0:
                        await self.use_one_time_effect(
                            ctx.author.id, 'next_gamble_multiplier'
                        )
                    await self.log_transaction(ctx.author.id, "gamble_win", win_amount)
                else:
                    await conn.execute(
                        """UPDATE economy 
                        SET wallet = wallet - $1 
                        WHERE user_id = $2""",
                        amount, ctx.author.id
                    )
                    await self.log_transaction(ctx.author.id, "gamble_loss", -amount)

                await self.bot.redis.incrby(f"daily_gambled:{ctx.author.id}", amount)
                if daily_gambled == 0:
                    await self.bot.redis.expire(f"daily_gambled:{ctx.author.id}", 86400)

        dice_str = ' '.join([dice_faces[r-1] for r in rolls])
        embed.description = (
            f"You rolled: **{dice_str}**\n"
            f"Hand: **{hand}**\n\n"
            f"{'🎉 You won' if won else '😢 You lost'} "
            f"**{amount:,}** coins!"
        )
        if won:
            embed.description += f"\n💫 {multiplier}x multiplier"
            if win_multiplier > 1.0:
                embed.description += f"\n🌟 Bonus multiplier: {win_multiplier}x"

        embed.color = discord.Color.green() if won else discord.Color.red()
        await msg.edit(embed=embed)

    @gamble.command(name="highcard")
    @is_econ_allowed()
    @commands.cooldown(1, 3, BucketType.user)
    async def high_card(self, ctx: Context, amount: str):
        """
        2-4 players draw cards, highest card wins the pot
        Each player must match the bet amount
        """
        if amount.lower() == 'all':
            wallet, _, _ = await self.get_balance(ctx.author.id)
            amount = wallet
        else:
            try:
                amount = int(amount.replace(',', ''))
            except ValueError:
                return await ctx.warn("Please provide a valid amount or `all`")

        if amount < 100:
            return await ctx.warn("Minimum bet is 100 coins!")

        daily_gambled = int(await self.bot.redis.get(f"daily_gambled:{ctx.author.id}") or 0)
        daily_limit = 1_000_000
        if daily_gambled + amount > daily_limit:
            remaining = daily_limit - daily_gambled
            return await ctx.warn(
                f"Daily gambling limit reached! You can only gamble {remaining:,} more coins today."
            )

        wallet, _, _ = await self.get_balance(ctx.author.id)
        if amount > wallet:
            return await ctx.warn("You don't have enough coins!")

        game_key = f"highcard:{ctx.channel.id}"
        if await self.bot.redis.exists(game_key):
            return await ctx.warn("A game is already in progress in this channel!")

        await self.bot.redis.setex(game_key, 60, "active")

        embed = Embed(
            title="🃏 High Card",
            description=(
                f"**{ctx.author.name}** started a high card game!\n"
                f"Buy-in: **{amount:,}** coins\n"
                f"React with 🃏 to join (2-4 players)\n"
                f"Game starts in 30 seconds"
            ),
            color=discord.Color.gold()
        )
        msg = await ctx.send(embed=embed)
        await msg.add_reaction("🃏")

        players = {ctx.author.id: ctx.author}
        start_time = time.time()

        def check(reaction, user):
            return (
                reaction.message.id == msg.id 
                and str(reaction.emoji) == "🃏"
                and user.id != ctx.author.id
                and user.id not in players
                and not user.bot
            )

        try:
            while time.time() - start_time < 30 and len(players) < 4:
                try:
                    reaction, user = await self.bot.wait_for(
                        'reaction_add',
                        timeout=max(1, 30 - (time.time() - start_time)),
                        check=check
                    )
                    
                    wallet = await self.bot.db.fetchval(
                        """SELECT wallet FROM economy WHERE user_id = $1""",
                        user.id
                    )
                    if not wallet or wallet < amount:
                        await ctx.warn(f"{user.mention} doesn't have enough coins!", delete_after=5)
                        continue

                    players[user.id] = user
                    embed.description = (
                        f"**{ctx.author.name}** started a high card game!\n"
                        f"Buy-in: **{amount:,}** coins\n"
                        f"Players ({len(players)}/4):\n"
                        + "\n".join(f"• {p.name}" for p in players.values())
                        + f"\nStarting in {int(30 - (time.time() - start_time))}s"
                    )
                    await msg.edit(embed=embed)

                except asyncio.TimeoutError:
                    continue

        except asyncio.TimeoutError:
            pass

        if len(players) < 2:
            await self.bot.redis.delete(game_key)
            return await ctx.warn("Not enough players joined!")

        cards = []
        card_values = {
            'A': 14, 'K': 13, 'Q': 12, 'J': 11,
            '10': 10, '9': 9, '8': 8, '7': 7,
            '6': 6, '5': 5, '4': 4, '3': 3, '2': 2
        }
        suits = ['♠️', '♥️', '♦️', '♣️']
        
        for player in players.values():
            value = random.choice(list(card_values.keys()))
            suit = random.choice(suits)
            cards.append({
                'player': player,
                'card': f"{value}{suit}",
                'value': card_values[value]
            })

        max_value = max(c['value'] for c in cards)
        winners = [c for c in cards if c['value'] == max_value]
        win_amount = amount * len(players) // len(winners)

        async with self.bot.db.acquire() as conn:
            async with conn.transaction():
                for player_id in players:
                    modifier = win_amount - amount if any(w['player'].id == player_id for w in winners) else -amount
                    await conn.execute(
                        """UPDATE economy 
                        SET wallet = wallet + $1 
                        WHERE user_id = $2""",
                        modifier, player_id
                    )
                    await self.log_transaction(
                        player_id,
                        "gamble_win" if modifier > 0 else "gamble_loss",
                        modifier
                    )

                    await self.bot.redis.incrby(f"daily_gambled:{player_id}", amount)
                    if not daily_gambled:
                        await self.bot.redis.expire(f"daily_gambled:{player_id}", 86400)

        results = []
        for card in cards:
            player = card['player']
            is_winner = any(w['player'].id == player.id for w in winners)
            results.append(
                f"• {player.name}: {card['card']} "
                f"{'🏆' if is_winner else ''}"
            )

        embed = Embed(
            title="🃏 High Card Results",
            description=(
                "\n".join(results)
                + f"\n\nWinners: {', '.join(w['player'].name for w in winners)}"
                + f"\nPrize: **{win_amount:,}** coins each"
            ),
            color=discord.Color.green()
        )
        await msg.edit(embed=embed)
        await self.bot.redis.delete(game_key)

    @gamble.command(name="mines")
    @is_econ_allowed()
    @commands.cooldown(1, 3, BucketType.user)
    async def mines_game(self, ctx: Context, bombs: int, amount: str):
        """
        Click squares to find gems while avoiding bombs!
        More bombs = higher risk but better multiplier
        1-15 bombs (more bombs = higher multiplier)
        Cashout anytime or hit a bomb and lose everything!
        """
        if not 1 <= bombs <= 15:
            return await ctx.warn("Please choose between 1-15 bombs!")

        if amount.lower() == 'all':
            wallet, _, _ = await self.get_balance(ctx.author.id)
            amount = wallet
        else:
            try:
                amount = int(amount.replace(',', ''))
            except ValueError:
                return await ctx.warn("Please provide a valid amount or `all`")

        if amount < 100:
            return await ctx.warn("Minimum bet is 100 coins!")

        daily_gambled = int(await self.bot.redis.get(f"daily_gambled:{ctx.author.id}") or 0)
        daily_limit = 1_000_000
        if daily_gambled + amount > daily_limit:
            remaining = daily_limit - daily_gambled
            return await ctx.warn(
                f"Daily gambling limit reached! You can only gamble {remaining:,} more coins today."
            )

        wallet, _, _ = await self.get_balance(ctx.author.id)
        if amount > wallet:
            return await ctx.warn("You don't have enough coins!")

        effects = await self.get_active_effects(ctx.author.id)
        luck_boost = effects.get('gambling_luck', {'value': 1.0})['value']
        win_multiplier = effects.get('next_gamble_multiplier', {'value': 1.0})['value']

        grid_size = 16
        bomb_positions = random.sample(range(grid_size), bombs)
        revealed = set()
        current_multiplier = 1.0

        class MinesView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=120.0)
                self.value = None
                
            @discord.ui.button(label="Cash Out 💰", style=discord.ButtonStyle.green, row=4)  
            async def cash_out(self, interaction: discord.Interaction):
                if interaction.user.id != interaction.message.interaction.user.id:
                    return await interaction.response.send_message(
                        "This isn't your game!", ephemeral=True
                    )
                self.value = "cashout"
                self.stop()
                await interaction.response.defer()

        view = MinesView()
        
        for i in range(grid_size):
            async def make_callback(pos):
                async def callback(interaction: discord.Interaction): 
                    if interaction.user.id != ctx.author.id:
                        return await interaction.response.send_message(
                            "This isn't your game!", ephemeral=True
                        )
                    
                    if pos in revealed:
                        return await interaction.response.send_message(
                            "This square is already revealed!", ephemeral=True
                        )
                        
                    revealed.add(pos)
                    
                    clicked_button = next(b for b in view.children 
                                        if isinstance(b, discord.ui.Button) 
                                        and hasattr(b, 'custom_id') 
                                        and b.custom_id == f"button_{pos}")
                    
                    if pos in bomb_positions:
                        for btn in view.children:
                            if isinstance(btn, discord.ui.Button):
                                btn.disabled = True
                                if hasattr(btn, 'custom_id'):
                                    try:
                                        if btn.custom_id and '_' in btn.custom_id:
                                            parts = btn.custom_id.split('_')
                                            if len(parts) >= 2:
                                                btn_pos = int(parts[1])
                                                if btn_pos in bomb_positions:
                                                    btn.style = discord.ButtonStyle.red
                                                    btn.label = "💣"
                                                else:
                                                    btn.style = discord.ButtonStyle.green
                                                    btn.label = "💎"
                                    except (IndexError, ValueError):
                                        continue

                        embed.description = (
                            f"💥 BOOM! You hit a bomb and lost everything!\n"
                            f"💣 **{bombs}** bombs placed\n"
                            f"💎 **{len([p for p in revealed if p not in bomb_positions])}** gems found"
                        )
                        embed.color = discord.Color.red()
                        
                        view.value = "bomb"
                        view.stop()
                    else:
                        clicked_button.style = discord.ButtonStyle.green
                        clicked_button.label = "💎"
                        clicked_button.disabled = True
                        
                        safe_revealed = len([p for p in revealed if p not in bomb_positions])
                        nonlocal current_multiplier
                        current_multiplier = Economy.calculate_multiplier(bombs, safe_revealed)
                        
                        embed.description = (
                            f"💣 **{bombs}** bombs placed\n"
                            f"💎 **{safe_revealed}** gems found\n"
                            f"Current multiplier: **{current_multiplier:.2f}x**\n"
                            f"Potential win: **{int(amount * current_multiplier):,}** coins"
                        )
                        
                    await interaction.response.edit_message(embed=embed, view=view)
                return callback

            row = i // 4
            button = discord.ui.Button(
                style=discord.ButtonStyle.gray,
                label="?",
                row=row,
                custom_id=f"button_{i}" 
            )
            button.callback = await make_callback(i)
            view.add_item(button)

        embed = Embed(
            description=(
                f"💣 **{bombs}** bombs placed\n"
                f"💎 **0** gems found\n"
                f"Current multiplier: **1.00x**\n"
                f"Potential win: **{amount:,}** coins"
            ),
            color=discord.Color.gold()
        )
        embed.add_field(
            name="Your Bet",
            value=f"**{amount:,}** coins"
        )
        if luck_boost > 1.0:
            embed.add_field(
                name="🍀 Luck Boost",
                value=f"+{(luck_boost-1)*100:.0f}% better odds"
            )

        msg = await ctx.send(embed=embed, view=view)
        win_amount = 0

        try:
            await view.wait()
        except TimeoutError:
            view.value = "timeout"

        if view.value == "bomb":
            for button in view.children:
                if isinstance(button, discord.ui.Button):
                    button.disabled = True
                    if hasattr(button, 'custom_id'):
                        try:
                            btn_pos = int(button.custom_id.split('_')[1])
                            if btn_pos in bomb_positions and button.label == "?":
                                button.style = discord.ButtonStyle.red
                                button.label = "💣"
                        except (IndexError, ValueError):
                            continue
        else:
            for button in view.children:
                if isinstance(button, discord.ui.Button):
                    button.disabled = True

        await msg.edit(view=view)

        if view.value == "timeout":
            embed.description = "Game ended due to inactivity!"
            win_amount = 0
        elif view.value == "bomb":
            embed.description = "💥 BOOM! You hit a bomb and lost everything!"
            win_amount = 0
        elif view.value == "cashout":
            win_amount = int(amount * current_multiplier * win_multiplier)
            embed.description = (
                f"🎉 Cashed out at **{current_multiplier:.2f}x**!\n"
                f"You won **{win_amount:,}** coins!"
            )
            if win_multiplier > 1.0:
                embed.description += f"\n🌟 Bonus multiplier: {win_multiplier}x"

        async with self.bot.db.acquire() as conn:
            async with conn.transaction():
                if win_amount > 0:
                    await conn.execute(
                        """UPDATE economy 
                        SET wallet = wallet + $1 
                        WHERE user_id = $2""",
                        win_amount - amount, ctx.author.id
                    )
                    if win_multiplier > 1.0:
                        await self.use_one_time_effect(
                            ctx.author.id, 'next_gamble_multiplier'
                        )
                    await self.log_transaction(ctx.author.id, "gamble_win", win_amount)
                else:
                    await conn.execute(
                        """UPDATE economy 
                        SET wallet = wallet - $1 
                        WHERE user_id = $2""",
                        amount, ctx.author.id
                    )
                    await self.log_transaction(ctx.author.id, "gamble_loss", -amount)

                await self.bot.redis.incrby(f"daily_gambled:{ctx.author.id}", amount)
                if daily_gambled == 0:
                    await self.bot.redis.expire(f"daily_gambled:{ctx.author.id}", 86400)

        embed.color = discord.Color.green() if win_amount > 0 else discord.Color.red()
        await msg.edit(embed=embed)

    @commands.group(name="arena", invoke_without_command=True)
    @is_econ_allowed()
    async def arena(self, ctx: Context):
        """View available arena games and tournaments"""
        embed = Embed(
            title="⚔️ Arena Games",
            description=(
                "**Available Games:**\n"
                "`arena duel <@user> <amount>` - 1v1 coin battle\n"
                "`arena create <entry_fee>` - Create a tournament\n"
                "`arena join <tournament_id>` - Join a tournament\n"
                "`arena list` - List active tournaments"
            ),
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)

    @arena.command(name="duel")
    @is_econ_allowed()
    @commands.cooldown(1, 30, BucketType.user)
    async def arena_duel(self, ctx: Context, opponent: Member, amount: str):
        """Challenge someone to a coin duel"""
        if opponent.bot:
            return await ctx.warn( "You can't duel bots!")
        
        if opponent.id == ctx.author.id:
            return await ctx.warn( "You can't duel yourself!")

        challenger_key = f"active_duel:{ctx.author.id}"
        opponent_key = f"active_duel:{opponent.id}"
        
        if await self.bot.redis.exists(challenger_key):
            return await ctx.warn( "You're already in a duel!")
        if await self.bot.redis.exists(opponent_key):
            return await ctx.warn( f"{opponent.name} is already in a duel!")

        if amount.lower() == "all":
            wallet, _, _ = await self.get_balance(ctx.author.id)
            amount = wallet
        else:
            try:
                amount = int(amount.replace(",", ""))
            except ValueError:
                return await ctx.warn( "Please provide a valid amount or `all`")

        if amount < 1000:
            return await ctx.warn( "Minimum duel amount is 1,000 coins!")

        challenger_wallet, _, _ = await self.get_balance(ctx.author.id)
        opponent_wallet, _, _ = await self.get_balance(opponent.id)

        if amount > challenger_wallet:
            return await ctx.warn( "You don't have enough coins!")
        if amount > opponent_wallet:
            return await ctx.warn( f"{opponent.name} doesn't have enough coins!")

        class DuelPrompt(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=30.0)
                self.value = None

            @discord.ui.button(label="Accept", style=discord.ButtonStyle.green)
            async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user != opponent:
                    return await interaction.response.send_message("This is not your duel to accept!", ephemeral=True)
                self.value = True
                self.stop()

            @discord.ui.button(label="Decline", style=discord.ButtonStyle.red)
            async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user != opponent:
                    return await interaction.response.send_message("This is not your duel to decline!", ephemeral=True)
                self.value = False
                self.stop()

        view = DuelPrompt()
        prompt = await ctx.send(
            f"{ctx.author.mention} has challenged you to a duel!\n"
            f"Wager: **{amount:,}** coins\n\n"
            f"Do you accept? {opponent.mention}",
            view=view
        )

        await view.wait()
        await prompt.delete()

        if not view.value:
            return await ctx.send(f"{opponent.name} declined the duel!")

        await self.bot.redis.setex(challenger_key, 300, "active")
        await self.bot.redis.setex(opponent_key, 300, "active")

        try:
            game = DuelGame(ctx.author, opponent, amount)
            view = DuelView(game)
            
            embed = Embed(
                title="⚔️ Coin Duel",
                description=(
                    f"{game.challenger.name}: ❤️ 100/100\n"
                    f"{game.opponent.name}: ❤️ 100/100\n\n"
                    f"Current turn: {game.current_turn.mention}\n\n"
                    "Moves:\n"
                    "⚔️ Attack: Medium damage, high accuracy\n"
                    "🛡️ Block: Reduce next damage and counter\n"
                    "🎯 Precise Strike: High damage, medium accuracy\n"
                    "💫 Special Move: Very high damage, low accuracy"
                ),
                color=discord.Color.gold()
            )
            msg = await ctx.send(embed=embed, view=view)

            await view.wait()
            view.stop()
            for button in view.children:
                button.disabled = True

            if view.value == "timeout":
                embed.description = "⏰ Duel timed out due to inactivity!"
                embed.color = discord.Color.red()
                await msg.edit(embed=embed, view=view)
                return

            if view.value == "tie":
                embed.description = (
                    "🤝 The duel ends in a tie!\n"
                    "Both fighters were evenly matched.\n"
                    "All coins have been returned."
                )
                embed.color = config.COLORS.NEUTRAL
                await msg.edit(embed=embed, view=view)
                return

            if view.value:
                winner = view.value
                loser = opponent if winner == ctx.author else ctx.author
                
                async with self.bot.db.acquire() as conn:
                    async with conn.transaction():
                        await conn.execute(
                            """UPDATE economy 
                            SET wallet = wallet + $1 
                            WHERE user_id = $2""",
                            amount, winner.id
                        )
                        await conn.execute(
                            """UPDATE economy 
                            SET wallet = wallet - $1 
                            WHERE user_id = $2""",
                            amount, loser.id
                        )

                embed.description = (
                    f"**{winner.name}** wins the duel!\n"
                    f"They won **{amount:,}** coins from {loser.name}!"
                )
                embed.color = discord.Color.green() if winner == ctx.author else discord.Color.red()
                await msg.edit(embed=embed, view=view)

        finally:
            await self.bot.redis.delete(challenger_key, opponent_key)

    @arena.command(name="create")
    @is_econ_allowed()
    @commands.cooldown(1, 60, BucketType.user)
    async def create_tournament(self, ctx: Context, entry_fee: str):
        """Create a tournament (max 8 players)"""
        user_key = f"active_duel:{ctx.author.id}"
        tournament_key = f"active_tournament:{ctx.author.id}"
        
        if await self.bot.redis.exists(user_key):
            return await ctx.warn( "You're already in a duel!")
        if await self.bot.redis.exists(tournament_key):
            return await ctx.warn( "You're already in a tournament!")

        try:
            entry_fee = int(entry_fee.replace(',', ''))
        except ValueError:
            return await ctx.warn( "Please provide a valid entry fee")

        if entry_fee < 1000:
            return await ctx.warn( "Minimum entry fee is 1,000 coins!")

        wallet, _, _ = await self.get_balance(ctx.author.id)
        if entry_fee > wallet:
            return await self.eco_warn("You don't have enough coins for the entry fee!")

        class TournamentView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60.0)
                self.participants = [ctx.author]
                self.started = False

            @discord.ui.button(label="Join Tournament", style=discord.ButtonStyle.green)
            async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user in self.participants:
                    return await interaction.response.send_message("You're already in the tournament!", ephemeral=True)
                
                if len(self.participants) >= 8:
                    return await interaction.response.send_message("Tournament is full!", ephemeral=True)

                user_key = f"active_duel:{interaction.user.id}"
                tournament_key = f"active_tournament:{interaction.user.id}"
                
                if await self.bot.redis.exists(user_key):
                    return await interaction.response.send_message("You're in an active duel!", ephemeral=True)
                if await self.bot.redis.exists(tournament_key):
                    return await interaction.response.send_message("You're already in a tournament!", ephemeral=True)

                wallet, _, _ = await self.bot.get_cog('Economy').get_balance(interaction.user.id)
                if wallet < entry_fee:
                    return await interaction.response.send_message("You don't have enough coins!", ephemeral=True)

                await self.bot.redis.setex(f"active_tournament:{interaction.user.id}", 3600, "active")
                
                self.participants.append(interaction.user)
                await interaction.response.send_message(f"You joined the tournament! ({len(self.participants)}/8)", ephemeral=True)
                
                embed = interaction.message.embeds[0]
                embed.description = (
                    f"Entry Fee: **{entry_fee:,}** coins\n"
                    f"Prize Pool: **{entry_fee * len(self.participants):,}** coins\n\n"
                    f"Players ({len(self.participants)}/8):\n" +
                    "\n".join(f"• {p.name}" for p in self.participants)
                )
                await interaction.message.edit(embed=embed)

        await self.bot.redis.setex(tournament_key, 3600, "active")

        try:
            view = TournamentView()
            embed = Embed(
                title="🏆 Tournament",
                description=(
                    f"Entry Fee: **{entry_fee:,}** coins\n"
                    f"Prize Pool: **{entry_fee:,}** coins\n\n"
                    "Players (1/8):\n"
                    f"• {ctx.author.name}"
                ),
                color=discord.Color.gold()
            )
            msg = await ctx.send(embed=embed, view=view)

            await view.wait()
            
            if not view.started:
                embed.description += "\n\n❌ Tournament cancelled!"
                embed.color = discord.Color.red()
                for child in view.children:
                    child.disabled = True
                return await msg.edit(embed=embed, view=view)

            participants = view.participants
            random.shuffle(participants)
            rounds = []
            current_round = []
            
            for i in range(0, len(participants), 2):
                current_round.append((participants[i], participants[i+1]))
            rounds.append(current_round)

            embed.description = (
                f"🏆 Tournament Started!\n"
                f"Prize Pool: **{entry_fee * len(participants):,}** coins\n\n"
                "Round 1 Matches:"
            )
            for i, (p1, p2) in enumerate(rounds[0], 1):
                embed.description += f"\nMatch {i}: {p1.name} vs {p2.name}"
            
            await msg.edit(embed=embed, view=None)

            winners = []
            round_num = 1
            
            for match in rounds[0]:
                player1, player2 = match
                
                duel_result = await self.run_duel(ctx, player1, player2, entry_fee)
                if duel_result:
                    winners.append(duel_result)
                    embed.description = (
                        f"🏆 Tournament Progress\n"
                        f"Round {round_num} - Match Result:\n"
                        f"**{duel_result.name}** defeated {player1.name if duel_result == player2 else player2.name}!"
                    )
                    await msg.edit(embed=embed)
                else:
                    embed.description += "\n❌ Match timed out!"
                    return await msg.edit(embed=embed)

            while len(winners) > 1:
                round_num += 1
                embed.description = f"🏆 Round {round_num} Matches:"
                current_round = []
                
                for i in range(0, len(winners), 2):
                    p1, p2 = winners[i], winners[i+1]
                    current_round.append((p1, p2))
                    embed.description += f"\n{p1.name} vs {p2.name}"
                
                await msg.edit(embed=embed)
                new_winners = []
                
                for match in current_round:
                    player1, player2 = match
                    duel_result = await self.run_duel(ctx, player1, player2, entry_fee)
                    if duel_result:
                        new_winners.append(duel_result)
                        embed.description = (
                            f"🏆 Tournament Progress\n"
                            f"Round {round_num} - Match Result:\n"
                            f"**{duel_result.name}** defeated {player1.name if duel_result == player2 else player2.name}!"
                        )
                        await msg.edit(embed=embed)
                    else:
                        embed.description += "\n❌ Match timed out!"
                        return await msg.edit(embed=embed)
                
                winners = new_winners

            winner = winners[0]
            prize_pool = entry_fee * len(participants)
            
            async with self.bot.db.acquire() as conn:
                async with conn.transaction():
                    await conn.execute(
                        """UPDATE economy 
                        SET wallet = wallet + $1 
                        WHERE user_id = $2""",
                        prize_pool, winner.id
                    )

            embed.description = (
                f"🏆 Tournament Complete!\n\n"
                f"Winner: **{winner.name}**\n"
                f"Prize: **{prize_pool:,}** coins!"
            )
            embed.color = discord.Color.green()
            await msg.edit(embed=embed)

        finally:
            for participant in view.participants:
                await self.bot.redis.delete(f"active_tournament:{participant.id}")

    async def run_duel(self, ctx, player1, player2, amount):
        """Run a single tournament duel"""
        game = DuelGame(player1, player2, amount)
        view = DuelView(game)
        
        embed = Embed(
            title="⚔️ Tournament Duel",
            description=(
                f"{game.challenger.name}: ❤️ 100/100\n"
                f"{game.opponent.name}: ❤️ 100/100\n\n"
                f"Current turn: {game.current_turn.mention}\n\n"
                "Moves:\n"
                "⚔️ Attack: Medium damage, high accuracy\n"
                "🛡️ Block: Reduce next damage and counter\n"
                "🎯 Precise Strike: High damage, medium accuracy\n"
                "💫 Special Move: Very high damage, low accuracy"
            ),
            color=discord.Color.gold()
        )
        msg = await ctx.send(embed=embed, view=view)

        await view.wait()
        view.stop()
        for button in view.children:
            button.disabled = True
        await msg.edit(view=view)

        return view.value

    @commands.group(name="leaderboard", aliases=["lb"], invoke_without_command=True)
    @is_econ_allowed()
    async def leaderboard(self, ctx: Context):
        """View the richest users"""
        async with self.bot.db.acquire() as conn:
            rows = await conn.fetch(
                """SELECT user_id, wallet + bank as total, wallet, bank 
                FROM economy 
                ORDER BY (wallet + bank) DESC 
                LIMIT 10"""
            )

        if not rows:
            return await ctx.warn("No users found!")

        embed = Embed(
            title="💰 Richest Users",
            color=discord.Color.gold()
        )

        description = []
        for i, row in enumerate(rows, 1):
            user = self.bot.get_user(row['user_id'])
            if not user:
                continue
            
            total = row['total']
            wallet = row['wallet']
            bank = row['bank']
            
            description.append(
                f"{i}. **{user.name}** - {total:,} coins\n"
                f"└ Wallet: {wallet:,} | Bank: {bank:,}"
            )

        embed.description = "\n".join(description)
        await ctx.send(embed=embed)

    @leaderboard.command(name="business", aliases=["biz"])
    @is_econ_allowed()
    async def leaderboard_business(self, ctx: Context):
        """View the most profitable businesses"""
        async with self.bot.db.acquire() as conn:
            rows = await conn.fetch(
                """SELECT * 
                FROM businesses 
                ORDER BY balance DESC 
                LIMIT 10"""
            )

        if not rows:
            return await ctx.warn("No businesses found!")

        embed = Embed(
            title="🏢 Top Businesses",
            color=discord.Color.gold()
        )

        description = []
        for i, row in enumerate(rows, 1):
            owner = ctx.guild.get_member(row['owner_id'])
            owner_name = owner.name if owner else "Unknown"
            
            description.append(
                f"{i}. **{row['name']}** (by {owner_name})\n"
                f"└ Balance: {row['balance']:,} coins | "
                f"Employees: {row['employee_limit']}"
            )

        embed.description = "\n".join(description)
        await ctx.send(embed=embed)

    @commands.group(name="pet", invoke_without_command=True)
    @is_econ_allowed()
    async def pet(self, ctx: Context):
        """Pet management commands"""
        await ctx.send_help(ctx.command)

    @pet.command(name="adopt")
    @is_econ_allowed()
    async def pet_adopt(self, ctx: Context, pet_type: str, name: str):
        """Adopt a new pet"""
        pet_type = pet_type.lower()
        if pet_type not in self.pet_types:
            return await ctx.warn(f"Invalid pet type! Available types: {', '.join(self.pet_types.keys())}")
            
        if len(name) > 32:
            return await ctx.warn("Pet name must be 32 characters or less!")

        pet_data = self.pet_types[pet_type]
        base_cost = pet_data["base_cost"]
        
        wallet, _, _ = await self.get_balance(ctx.author.id)
        if wallet < base_cost:
            return await ctx.warn(f"You need {base_cost:,} coins to adopt a {pet_type}!")

        rarity = random.choices(
            list(pet_data["rarity_weights"].keys()),
            weights=list(pet_data["rarity_weights"].values())
        )[0]

        async with self.bot.db.acquire() as conn:
            async with conn.transaction():
                pet_id = await conn.fetchval(
                    """INSERT INTO pets (
                        owner_id, name, type, rarity
                    ) VALUES ($1, $2, $3, $4)
                    RETURNING pet_id""",
                    ctx.author.id, name, pet_type, rarity
                )
                
                await conn.execute(
                    """UPDATE economy 
                    SET wallet = wallet - $1 
                    WHERE user_id = $2""",
                    base_cost, ctx.author.id
                )

        embed = Embed(
            title="🎉 New Pet Adopted!",
            description=(
                f"You adopted a {self.pet_types[pet_type]['emoji']} "
                f"**{rarity.title()} {pet_type.title()}**!\n"
                f"Say hello to **{name}**!"
            ),
            color=self.rarity_colors[rarity]
        )
        await ctx.send(embed=embed)

    @pet.command(name="list")
    @is_econ_allowed()
    async def pet_list(self, ctx: Context):
        """List all your pets"""
        async with self.bot.db.acquire() as conn:
            pets = await conn.fetch(
                """SELECT * FROM pets WHERE owner_id = $1 ORDER BY active DESC, level DESC""",
                ctx.author.id
            )

        if not pets:
            return await ctx.warn("You don't have any pets! Use `pet adopt` to get one.")

        embed = Embed(
            title="🐾 Your Pets",
            color=discord.Color.blue()
        )

        for pet in pets:
            status = "🟢" if pet["active"] else "⚪"
            emoji = self.pet_types[pet["type"]]["emoji"]
            
            embed.add_field(
                name=f"{status} {emoji} {pet['name']}",
                value=(
                    f"Type: {pet['type'].title()}\n"
                    f"Rarity: {pet['rarity'].title()}\n"
                    f"Level: {pet['level']}\n"
                    f"XP: {pet['xp']}"
                ),
                inline=True
            )

        await ctx.send(embed=embed)

    @pet.command(name="info")
    @is_econ_allowed()
    async def pet_info(self, ctx: Context, *, name: str):
        """View detailed information about a pet"""
        async with self.bot.db.acquire() as conn:
            pet = await conn.fetchrow(
                """SELECT * FROM pets 
                WHERE owner_id = $1 AND LOWER(name) = LOWER($2)""",
                ctx.author.id, name
            )

        if not pet:
            return await ctx.warn("Pet not found!")

        pet_type = self.pet_types[pet["type"]]
        embed = Embed(
            title=f"{pet_type['emoji']} {pet['name']}",
            color=self.rarity_colors[pet["rarity"]]
        )
        
        embed.add_field(
            name="Details",
            value=(
                f"Type: {pet['type'].title()}\n"
                f"Rarity: {pet['rarity'].title()}\n"
                f"Level: {pet['level']}\n"
                f"XP: {pet['xp']}/100"
            )
        )
        
        embed.add_field(
            name="Stats",
            value=(
                f"❤️ Health: {pet['health']}/100\n"
                f"😊 Happiness: {pet['happiness']}/100\n"
                f"🍖 Hunger: {pet['hunger']}/100"
            )
        )
        
        embed.add_field(
            name="Abilities",
            value="\n".join(f"• {ability}" for ability in pet_type["abilities"]),
            inline=False
        )

        await ctx.send(embed=embed)

    @pet.command(name="active")
    @is_econ_allowed()
    async def pet_active(self, ctx: Context, *, name: str):
        """Set your active pet"""
        async with self.bot.db.acquire() as conn:
            pet = await conn.fetchrow(
                """SELECT * FROM pets 
                WHERE owner_id = $1 AND LOWER(name) = LOWER($2)""",
                ctx.author.id, name
            )
            
            if not pet:
                return await ctx.warn("Pet not found!")

            async with conn.transaction():
                await conn.execute(
                    """UPDATE pets SET active = false 
                    WHERE owner_id = $1 AND active = true""",
                    ctx.author.id
                )
                
                await conn.execute(
                    """UPDATE pets SET active = true 
                    WHERE pet_id = $1""",
                    pet["pet_id"]
                )

        await ctx.approve(f"**{pet['name']}** is now your active pet!")

    @pet.command(name="feed")
    @is_econ_allowed()
    @commands.cooldown(1, 1800, BucketType.user)  
    async def pet_feed(self, ctx: Context, *, name: str):
        """Feed your pet to restore hunger"""
        async with self.bot.db.acquire() as conn:
            pet = await conn.fetchrow(
                """SELECT * FROM pets 
                WHERE owner_id = $1 AND LOWER(name) = LOWER($2)""",
                ctx.author.id, name
            )
            
            if not pet:
                return await ctx.warn("Pet not found!")

            if pet["hunger"] >= 100:
                ctx.command.reset_cooldown(ctx)
                return await ctx.warn(f"**{pet['name']}** isn't hungry!")

            feed_cost = 100 * (1 + pet["level"] // 10)
            wallet, _, _ = await self.get_balance(ctx.author.id)
            
            if wallet < feed_cost:
                return await ctx.warn(f"You need {feed_cost:,} coins to feed your pet!")

            hunger_increase = random.randint(20, 40)
            new_hunger = min(100, pet["hunger"] + hunger_increase)
            xp_gain = random.randint(1, 3)

            async with conn.transaction():
                await conn.execute(
                    """UPDATE pets 
                    SET hunger = $1, xp = xp + $2 
                    WHERE pet_id = $3""",
                    new_hunger, xp_gain, pet["pet_id"]
                )
                
                await conn.execute(
                    """UPDATE economy 
                    SET wallet = wallet - $1 
                    WHERE user_id = $2""",
                    feed_cost, ctx.author.id
                )

        await ctx.approve(
            f"Fed **{pet['name']}**!\n"
            f"Hunger: {pet['hunger']} → {new_hunger}\n"
            f"XP gained: {xp_gain}"
        )

    @pet.command(name="play")
    @is_econ_allowed()
    @commands.cooldown(1, 3600, BucketType.user) 
    async def pet_play(self, ctx: Context, *, name: str):
        """Play with your pet to increase happiness"""
        async with self.bot.db.acquire() as conn:
            pet = await conn.fetchrow(
                """SELECT * FROM pets 
                WHERE owner_id = $1 AND LOWER(name) = LOWER($2)""",
                ctx.author.id, name
            )
            
            if not pet:
                return await ctx.warn("Pet not found!")

            if pet["happiness"] >= 100:
                ctx.command.reset_cooldown(ctx)
                return await ctx.warn(f"**{pet['name']}** is already at maximum happiness!")

            happiness_increase = random.randint(15, 30)
            new_happiness = min(100, pet["happiness"] + happiness_increase)
            xp_gain = random.randint(3, 8)

            hunger_decrease = random.randint(5, 15)
            new_hunger = max(0, pet["hunger"] - hunger_decrease)

            await conn.execute(
                """UPDATE pets 
                SET happiness = $1, hunger = $2, xp = xp + $3 
                WHERE pet_id = $4""",
                new_happiness, new_hunger, xp_gain, pet["pet_id"]
            )

        await ctx.approve(
            f"Played with **{pet['name']}**!\n"
            f"Happiness: {pet['happiness']} → {new_happiness}\n"
            f"Hunger: {pet['hunger']} → {new_hunger}\n"
            f"XP gained: {xp_gain}"
        )

    @pet.command(name="train")
    @is_econ_allowed()
    @commands.cooldown(1, 7200, BucketType.user)  
    async def pet_train(self, ctx: Context, *, name: str):
        """Train your pet to gain XP"""
        async with self.bot.db.acquire() as conn:
            pet = await conn.fetchrow(
                """SELECT * FROM pets 
                WHERE owner_id = $1 AND LOWER(name) = LOWER($2)""",
                ctx.author.id, name
            )
            
            if not pet:
                return await ctx.warn("Pet not found!")

            if pet["hunger"] < 30:
                ctx.command.reset_cooldown(ctx)
                return await ctx.warn(f"**{pet['name']}** is too hungry to train!")

            if pet["happiness"] < 30:
                ctx.command.reset_cooldown(ctx)
                return await ctx.warn(f"**{pet['name']}** is too unhappy to train!")

            training_cost = 500 * (1 + pet["level"] // 5)
            wallet, _, _ = await self.get_balance(ctx.author.id)
            
            if wallet < training_cost:
                return await ctx.warn(f"You need {training_cost:,} coins to train your pet!")

            xp_gain = random.randint(10, 20)
            new_xp = pet["xp"] + xp_gain
            new_level = pet["level"]
            level_up = False

            if new_xp >= 100:
                new_level += 1
                new_xp -= 100
                level_up = True

            happiness_decrease = random.randint(10, 20)
            hunger_decrease = random.randint(15, 25)
            
            new_happiness = max(0, pet["happiness"] - happiness_decrease)
            new_hunger = max(0, pet["hunger"] - hunger_decrease)

            async with conn.transaction():
                await conn.execute(
                    """UPDATE pets 
                    SET xp = $1, level = $2, happiness = $3, hunger = $4 
                    WHERE pet_id = $5""",
                    new_xp, new_level, new_happiness, new_hunger, pet["pet_id"]
                )
                
                await conn.execute(
                    """UPDATE economy 
                    SET wallet = wallet - $1 
                    WHERE user_id = $2""",
                    training_cost, ctx.author.id
                )

        response = [f"Trained **{pet['name']}**!"]
        if level_up:
            response.append(f"🎉 Level up! {pet['level']} → {new_level}")
        response.extend([
            f"XP: {pet['xp']} → {new_xp}",
            f"Happiness: {pet['happiness']} → {new_happiness}",
            f"Hunger: {pet['hunger']} → {new_hunger}"
        ])

        await ctx.approve("\n".join(response))

    @pet.command(name="shop")
    @is_econ_allowed()
    async def pet_shop(self, ctx: Context):
        """View pet shop items"""
        shop_items = {
            "basic_food": {
                "name": "Basic Food",
                "emoji": "🥫",
                "cost": 500,
                "hunger": 25,
                "description": "Restores 25 hunger"
            },
            "premium_food": {
                "name": "Premium Food",
                "emoji": "🍖",
                "cost": 1500,
                "hunger": 50,
                "happiness": 10,
                "description": "Restores 50 hunger and 10 happiness"
            },
            "toy": {
                "name": "Pet Toy",
                "emoji": "🧸",
                "cost": 2000,
                "happiness": 30,
                "description": "Restores 30 happiness"
            }
        }

        embed = Embed(
            title="🏪 Pet Shop",
            description="Use `pet buy <item> <pet_name>` to purchase",
            color=discord.Color.blue()
        )

        for item_id, item in shop_items.items():
            embed.add_field(
                name=f"{item['emoji']} {item['name']} - {item['cost']:,} coins",
                value=item['description'],
                inline=False
            )

        await ctx.send(embed=embed)

    @pet.command(name="buy")
    @is_econ_allowed()
    async def pet_buy(self, ctx: Context, item: str, *, pet_name: str):
        """Buy an item for your pet"""
        shop_items = {
            "basic_food": {
                "name": "Basic Food",
                "emoji": "🥫",
                "cost": 500,
                "hunger": 25
            },
            "premium_food": {
                "name": "Premium Food",
                "emoji": "🍖",
                "cost": 1500,
                "hunger": 50,
                "happiness": 10
            },
            "toy": {
                "name": "Pet Toy",
                "emoji": "🧸",
                "cost": 2000,
                "happiness": 30
            }
        }

        item = item.lower()
        if item not in shop_items:
            return await ctx.warn(f"Invalid item! Use `pet shop` to see available items.")

        item_data = shop_items[item]
        wallet, _, _ = await self.get_balance(ctx.author.id)
        
        if wallet < item_data["cost"]:
            return await ctx.warn(f"You need {item_data['cost']:,} coins to buy this!")

        async with self.bot.db.acquire() as conn:
            pet = await conn.fetchrow(
                """SELECT * FROM pets 
                WHERE owner_id = $1 AND LOWER(name) = LOWER($2)""",
                ctx.author.id, pet_name
            )
            
            if not pet:
                return await ctx.warn("Pet not found!")

            new_hunger = min(100, pet["hunger"] + item_data.get("hunger", 0))
            new_happiness = min(100, pet["happiness"] + item_data.get("happiness", 0))

            async with conn.transaction():
                await conn.execute(
                    """UPDATE pets 
                    SET hunger = $1, happiness = $2 
                    WHERE pet_id = $3""",
                    new_hunger, new_happiness, pet["pet_id"]
                )
                
                await conn.execute(
                    """UPDATE economy 
                    SET wallet = wallet - $1 
                    WHERE user_id = $2""",
                    item_data["cost"], ctx.author.id
                )

        response = [f"Gave {item_data['emoji']} **{item_data['name']}** to **{pet['name']}**!"]
        if "hunger" in item_data:
            response.append(f"Hunger: {pet['hunger']} → {new_hunger}")
        if "happiness" in item_data:
            response.append(f"Happiness: {pet['happiness']} → {new_happiness}")

        await ctx.approve("\n".join(response))

    @pet.command(name="adventure")
    @is_econ_allowed()
    async def pet_adventure(self, ctx: Context, *, name: str):
        """Send your pet on an adventure"""
        async with self.bot.db.acquire() as conn:
            pet = await conn.fetchrow(
                """SELECT * FROM pets 
                WHERE owner_id = $1 AND LOWER(name) = LOWER($2)""",
                ctx.author.id, name
            )
            
            if not pet:
                return await ctx.warn("Pet not found!")

            active_adventure = await conn.fetchrow(
                """SELECT * FROM pet_adventures 
                WHERE pet_id = $1 AND completed = false""",
                pet["pet_id"]
            )
            
            if active_adventure:
                end_time = active_adventure["end_time"]
                if end_time > datetime.now():
                    time_left = end_time - datetime.now()
                    minutes = int(time_left.total_seconds() / 60)
                    return await ctx.warn(
                        f"**{pet['name']}** is already on an adventure!\n"
                        f"Time remaining: {minutes} minutes"
                    )

            if pet["hunger"] < 30:
                return await ctx.warn(f"**{pet['name']}** is too hungry to go on an adventure!")

            if pet["happiness"] < 30:
                return await ctx.warn(f"**{pet['name']}** is too unhappy to go on an adventure!")

            adventures = {
                "short": {
                    "duration": 30,  
                    "min_level": 1,
                    "coin_range": (100, 500),
                    "xp_range": (5, 15)
                },
                "medium": {
                    "duration": 60,
                    "min_level": 5,
                    "coin_range": (300, 1000),
                    "xp_range": (10, 25)
                },
                "long": {
                    "duration": 120,
                    "min_level": 10,
                    "coin_range": (800, 2000),
                    "xp_range": (20, 40)
                }
            }

            available_adventures = {
                k: v for k, v in adventures.items() 
                if pet["level"] >= v["min_level"]
            }

            if not available_adventures:
                return await ctx.warn("No adventures available for your pet's level!")

            embed = Embed(
                title="🗺️ Available Adventures",
                description=f"Choose an adventure for **{pet['name']}**",
                color=discord.Color.blue()
            )

            for adv_type, data in available_adventures.items():
                embed.add_field(
                    name=f"{adv_type.title()} Adventure",
                    value=(
                        f"Duration: {data['duration']} minutes\n"
                        f"Coins: {data['coin_range'][0]:,} - {data['coin_range'][1]:,}\n"
                        f"XP: {data['xp_range'][0]} - {data['xp_range'][1]}"
                    ),
                    inline=False
                )

            class AdventureView(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=30.0)
                    self.value = None

                @discord.ui.button(label="Short", style=discord.ButtonStyle.primary)
                async def short(self, interaction: discord.Interaction, button: discord.ui.Button):
                    if interaction.user.id != ctx.author.id:
                        return
                    self.value = "short"
                    self.stop()

                @discord.ui.button(label="Medium", style=discord.ButtonStyle.primary)
                async def medium(self, interaction: discord.Interaction, button: discord.ui.Button):
                    if interaction.user.id != ctx.author.id:
                        return
                    if pet["level"] < 5:
                        return await interaction.response.send_message("Pet level too low!", ephemeral=True)
                    self.value = "medium"
                    self.stop()

                @discord.ui.button(label="Long", style=discord.ButtonStyle.primary)
                async def long(self, interaction: discord.Interaction, button: discord.ui.Button):
                    if interaction.user.id != ctx.author.id:
                        return
                    if pet["level"] < 10:
                        return await interaction.response.send_message("Pet level too low!", ephemeral=True)
                    self.value = "long"
                    self.stop()

            view = AdventureView()
            msg = await ctx.send(embed=embed, view=view)
            await view.wait()

            if not view.value:
                return await ctx.warn("No adventure selected!")

            selected = adventures[view.value]
            end_time = datetime.now() + timedelta(minutes=selected["duration"])

            await conn.execute(
                """INSERT INTO pet_adventures (
                    pet_id, adventure_type, start_time, end_time
                ) VALUES ($1, $2, CURRENT_TIMESTAMP, $3)""",
                pet["pet_id"], view.value, end_time
            )

            embed = Embed(
                title="🗺️ Adventure Started!",
                description=(
                    f"**{pet['name']}** has embarked on a {view.value} adventure!\n"
                    f"Duration: {selected['duration']} minutes\n"
                    f"Return to collect rewards with `pet collect {pet['name']}`"
                ),
                color=discord.Color.green()
            )
            await msg.edit(embed=embed, view=None)

    @pet.command(name="collect")
    @is_econ_allowed()
    async def collect_adventure(self, ctx: Context, *, name: str):
        """Collect rewards from your pet's adventure"""
        async with self.bot.db.acquire() as conn:
            pet = await conn.fetchrow(
                """SELECT * FROM pets 
                WHERE owner_id = $1 AND LOWER(name) = LOWER($2)""",
                ctx.author.id, name
            )
            
            if not pet:
                return await ctx.warn("Pet not found!")

            adventure = await conn.fetchrow(
                """SELECT * FROM pet_adventures 
                WHERE pet_id = $1 AND completed = false""",
                pet["pet_id"]
            )

            if not adventure:
                return await ctx.warn(f"**{pet['name']}** isn't on an adventure!")

            if adventure["end_time"] > datetime.now():
                time_left = adventure["end_time"] - datetime.now()
                minutes = int(time_left.total_seconds() / 60)
                return await ctx.warn(
                    f"**{pet['name']}**'s adventure isn't complete yet!\n"
                    f"Time remaining: {minutes} minutes"
                )

            adventures = {
                "short": {
                    "coin_range": (100, 500),
                    "xp_range": (5, 15)
                },
                "medium": {
                    "coin_range": (300, 1000),
                    "xp_range": (10, 25)
                },
                "long": {
                    "coin_range": (800, 2000),
                    "xp_range": (20, 40)
                }
            }

            adv_type = adventure["adventure_type"]
            adv_data = adventures[adv_type]

            coins = random.randint(*adv_data["coin_range"])
            xp = random.randint(*adv_data["xp_range"])
            
            rarity_multipliers = {
                "common": 1.0,
                "uncommon": 1.2,
                "rare": 1.5,
                "epic": 2.0,
                "legendary": 3.0
            }
            
            coins = int(coins * rarity_multipliers[pet["rarity"]])
            
            new_xp = pet["xp"] + xp
            new_level = pet["level"]
            level_up = False

            if new_xp >= 100:
                new_level += 1
                new_xp -= 100
                level_up = True

            happiness_decrease = random.randint(10, 20)
            hunger_decrease = random.randint(15, 25)
            
            new_happiness = max(0, pet["happiness"] - happiness_decrease)
            new_hunger = max(0, pet["hunger"] - hunger_decrease)

            async with conn.transaction():
                await conn.execute(
                    """UPDATE pets 
                    SET xp = $1, level = $2, happiness = $3, hunger = $4 
                    WHERE pet_id = $5""",
                    new_xp, new_level, new_happiness, new_hunger, pet["pet_id"]
                )
                
                await conn.execute(
                    """UPDATE economy 
                    SET wallet = wallet + $1 
                    WHERE user_id = $2""",
                    coins, ctx.author.id
                )
                
                await conn.execute(
                    """UPDATE pet_adventures 
                    SET completed = true 
                    WHERE pet_id = $1 AND completed = false""",
                    pet["pet_id"]
                )

            response = [
                f"**{pet['name']}** returned from their {adv_type} adventure!",
                f"Coins earned: {coins:,}",
                f"XP gained: {xp}"
            ]
            
            if level_up:
                response.append(f"🎉 Level up! {pet['level']} → {new_level}")
            
            response.extend([
                f"Happiness: {pet['happiness']} → {new_happiness}",
                f"Hunger: {pet['hunger']} → {new_hunger}"
            ])

            await ctx.approve("\n".join(response))

    @pet.command(name="rename")
    @is_econ_allowed()
    async def pet_rename(self, ctx: Context, pet_name: str, new_name: str):
        """Rename your pet (costs 5,000 coins)"""
        if len(new_name) > 32:
            return await ctx.warn("New name must be 32 characters or less!")

        rename_cost = 5000
        wallet, _, _ = await self.get_balance(ctx.author.id)
        
        if wallet < rename_cost:
            return await ctx.warn(f"You need {rename_cost:,} coins to rename your pet!")

        async with self.bot.db.acquire() as conn:
            pet = await conn.fetchrow(
                """SELECT * FROM pets 
                WHERE owner_id = $1 AND LOWER(name) = LOWER($2)""",
                ctx.author.id, pet_name
            )
            
            if not pet:
                return await ctx.warn("Pet not found!")

            existing = await conn.fetchrow(
                """SELECT * FROM pets 
                WHERE owner_id = $1 AND LOWER(name) = LOWER($2)""",
                ctx.author.id, new_name
            )
            
            if existing:
                return await ctx.warn("You already have a pet with that name!")

            async with conn.transaction():
                await conn.execute(
                    """UPDATE pets SET name = $1 WHERE pet_id = $2""",
                    new_name, pet["pet_id"]
                )
                
                await conn.execute(
                    """UPDATE economy 
                    SET wallet = wallet - $1 
                    WHERE user_id = $2""",
                    rename_cost, ctx.author.id
                )

        await ctx.approve(
            f"Renamed your pet from **{pet['name']}** to **{new_name}**!\n"
            f"Cost: {rename_cost:,} coins"
        )

    @pet.command(name="skills")
    @is_econ_allowed()
    async def pet_skills(self, ctx: Context, *, name: str = None):
        """View pet skills and abilities"""
        async with self.bot.db.acquire() as conn:
            if name:
                pet = await conn.fetchrow(
                    """SELECT * FROM pets 
                    WHERE owner_id = $1 AND LOWER(name) = LOWER($2)""",
                    ctx.author.id, name
                )
                
                if not pet:
                    return await ctx.warn("Pet not found!")

                pet_type = self.pet_types[pet["type"]]
                abilities = []
                
                if pet["level"] >= 5:
                    abilities.append(pet_type["abilities"][0])
                if pet["level"] >= 15:
                    abilities.append("Training Boost")
                if pet["level"] >= 25:
                    abilities.append("Adventure Expert")
                
                embed = Embed(
                    title=f"{pet_type['emoji']} {pet['name']}'s Abilities",
                    color=self.rarity_colors[pet["rarity"]]
                )
                
                for ability in abilities:
                    embed.add_field(
                        name=ability,
                        value=self.get_ability_description(ability, pet),
                        inline=False
                    )
                
                if not abilities:
                    embed.description = "No abilities unlocked yet! Level up to unlock abilities."
            else:
                embed = Embed(
                    title="🎯 Pet Abilities",
                    description="Different pets unlock different abilities as they level up!",
                    color=discord.Color.blue()
                )
                
                for pet_type, data in self.pet_types.items():
                    abilities = [
                        "• Level 5: " + data["abilities"][0],
                        "• Level 15: Training Boost",
                        "• Level 25: Adventure Expert"
                    ]
                    embed.add_field(
                        name=f"{data['emoji']} {data['name']}",
                        value="\n".join(abilities),
                        inline=False
                    )
            
            await ctx.send(embed=embed)

    def get_ability_description(self, ability: str, pet: dict) -> str:
        """Get the description of a pet ability"""
        rarity_multiplier = {
            "common": 1.0,
            "uncommon": 1.2,
            "rare": 1.5,
            "epic": 2.0,
            "legendary": 3.0
        }[pet["rarity"]]
        
        descriptions = {
            "coin_finder": f"Find {int(15 * rarity_multiplier)}% more coins from work",
            "critical_boost": f"{int(10 * rarity_multiplier)}% chance for critical hits in battles",
            "battle_master": f"Deal {int(20 * rarity_multiplier)}% more damage in battles",
            "Training Boost": "Gain 25% more XP from training",
            "Adventure Expert": "10% faster adventure completion"
        }
        return descriptions.get(ability, "No description available")

    @pet.command(name="battle")
    @is_econ_allowed()
    @commands.cooldown(1, 300, BucketType.user)  
    async def pet_battle(self, ctx: Context, opponent: Member, bet: int = 0):
        """Battle another user's pet"""
        if opponent.bot or opponent == ctx.author:
            return await ctx.warn("You can't battle with that user!")
            
        if bet < 0:
            return await ctx.warn("Bet amount cannot be negative!")
            
        if bet > 0:
            wallet, _, _ = await self.get_balance(ctx.author.id)
            if wallet < bet:
                return await ctx.warn("You don't have enough coins!")
                
            opp_wallet, _, _ = await self.get_balance(opponent.id)
            if opp_wallet < bet:
                return await ctx.warn(f"{opponent.name} doesn't have enough coins!")

        async with self.bot.db.acquire() as conn:
            challenger_pet = await conn.fetchrow(
                """SELECT * FROM pets 
                WHERE owner_id = $1 AND active = true""",
                ctx.author.id
            )
            
            opponent_pet = await conn.fetchrow(
                """SELECT * FROM pets 
                WHERE owner_id = $1 AND active = true""",
                opponent.id
            )
            
            if not challenger_pet:
                return await ctx.warn("You need an active pet to battle! Use `pet active` to set one.")
            
            if not opponent_pet:
                return await ctx.warn(f"{opponent.name} doesn't have an active pet!")
                
            if challenger_pet["hunger"] < 20 or challenger_pet["happiness"] < 20:
                return await ctx.warn("Your pet is too tired to battle!")
                
            if opponent_pet["hunger"] < 20 or opponent_pet["happiness"] < 20:
                return await ctx.warn(f"{opponent.name}'s pet is too tired to battle!")

        embed = Embed(
            title="⚔️ Pet Battle Challenge",
            description=(
                f"{ctx.author.mention} challenges {opponent.mention} to a pet battle!\n"
                f"**{challenger_pet['name']}** VS **{opponent_pet['name']}**\n"
                f"Bet amount: {bet:,} coins\n\n"
                f"{opponent.mention}, do you accept?"
            ),
            color=discord.Color.orange()
        )
        
        class BattleView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=30.0)
                self.value = None

            @discord.ui.button(label="Accept", style=discord.ButtonStyle.green)
            async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user.id != opponent.id:
                    return
                self.value = True
                self.stop()

            @discord.ui.button(label="Decline", style=discord.ButtonStyle.red)
            async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user.id != opponent.id:
                    return
                self.value = False
                self.stop()

        view = BattleView()
        msg = await ctx.send(embed=embed, view=view)
        await view.wait()

        if view.value is None:
            await msg.edit(content="Challenge timed out!", embed=None, view=None)
            return
            
        if not view.value:
            await msg.edit(content="Challenge declined!", embed=None, view=None)
            return

        battle = PetBattle(ctx, opponent, challenger_pet, opponent_pet, bet)
        await battle.start_battle(msg)

    @pet.command(name="breed")
    @is_econ_allowed()
    @commands.cooldown(1, 86400, BucketType.user)
    async def pet_breed(self, ctx: Context, pet1_name: str, pet2_name: str):
        """Breed two pets for a chance at rare offspring (costs 25,000 coins)"""
        if pet1_name.lower() == pet2_name.lower():
            return await ctx.warn("You can't breed a pet with itself!")

        breed_cost = 25000
        wallet, _, _ = await self.get_balance(ctx.author.id)
        
        if wallet < breed_cost:
            return await ctx.warn(f"You need {breed_cost:,} coins to breed pets!")

        async with self.bot.db.acquire() as conn:
            pet1 = await conn.fetchrow(
                """SELECT * FROM pets 
                WHERE owner_id = $1 AND LOWER(name) = LOWER($2)""",
                ctx.author.id, pet1_name
            )
            
            pet2 = await conn.fetchrow(
                """SELECT * FROM pets 
                WHERE owner_id = $1 AND LOWER(name) = LOWER($2)""",
                ctx.author.id, pet2_name
            )

            if not pet1 or not pet2:
                return await ctx.warn("One or both pets not found!")

            min_level = 15
            if pet1["level"] < min_level or pet2["level"] < min_level:
                return await ctx.warn(f"Both pets must be at least level {min_level} to breed!")

            rarity_levels = ["common", "uncommon", "rare", "epic", "legendary"]
            parent_rarities = [rarity_levels.index(pet1["rarity"]), rarity_levels.index(pet2["rarity"])]
            max_rarity = max(parent_rarities)
            
            same_type_bonus = 0.1 if pet1["type"] == pet2["type"] else 0
            
            rarity_chances = {
                "legendary": 0.05 + (0.02 * max_rarity) + same_type_bonus,
                "epic": 0.15 + (0.03 * max_rarity) + same_type_bonus,
                "rare": 0.25 + (0.04 * max_rarity) + same_type_bonus,
                "uncommon": 0.30,
                "common": 0.25
            }

            offspring_rarity = random.choices(
                list(rarity_chances.keys()),
                weights=list(rarity_chances.values())
            )[0]

            offspring_type = random.choice([pet1["type"], pet2["type"]])
            
            base_name = f"Baby {offspring_type.title()}"
            suffix = 1
            offspring_name = base_name
            
            while await conn.fetchrow(
                """SELECT 1 FROM pets 
                WHERE owner_id = $1 AND LOWER(name) = LOWER($2)""",
                ctx.author.id, offspring_name
            ):
                suffix += 1
                offspring_name = f"{base_name} {suffix}"

            async with conn.transaction():
                await conn.execute(
                    """INSERT INTO pets (
                        owner_id, name, type, rarity, 
                        happiness, hunger
                    ) VALUES ($1, $2, $3, $4, 100, 100)""",
                    ctx.author.id, offspring_name, offspring_type, offspring_rarity
                )
                
                await conn.execute(
                    """UPDATE economy 
                    SET wallet = wallet - $1 
                    WHERE user_id = $2""",
                    breed_cost, ctx.author.id
                )

        embed = Embed(
            title="🎉 New Pet Born!",
            description=(
                f"**{pet1['name']}** and **{pet2['name']}** had a baby!\n"
                f"Say hello to **{offspring_name}**!\n\n"
                f"Type: {self.pet_types[offspring_type]['emoji']} {offspring_type.title()}\n"
                f"Rarity: {offspring_rarity.title()}\n"
                f"Cost: {breed_cost:,} coins"
            ),
            color=self.rarity_colors[offspring_rarity]
        )
        await ctx.send(embed=embed)

    @pet.command(name="collection")
    @is_econ_allowed()
    async def pet_collection(self, ctx: Context):
        """View your pet collection progress"""
        async with self.bot.db.acquire() as conn:
            pets = await conn.fetch(
                "SELECT type, rarity FROM pets WHERE owner_id = $1",
                ctx.author.id
            )

        if not pets:
            return await ctx.warn("You don't have any pets in your collection!")

        collection = {}
        for pet_type in self.pet_types:
            collection[pet_type] = {
                "common": False,
                "uncommon": False,
                "rare": False,
                "epic": False,
                "legendary": False
            }

        for pet in pets:
            collection[pet["type"]][pet["rarity"]] = True

        total_combinations = len(self.pet_types) * 5  
        collected = sum(
            sum(1 for rarity in type_data.values() if rarity)
            for type_data in collection.values()
        )
        completion_percent = (collected / total_combinations) * 100

        embed = Embed(
            title="📚 Pet Collection",
            description=(
                f"Collection Progress: {collected}/{total_combinations} "
                f"({completion_percent:.1f}%)"
            ),
            color=discord.Color.blue()
        )

        for pet_type, rarities in collection.items():
            type_data = self.pet_types[pet_type]
            status = []
            for rarity, collected in rarities.items():
                emoji = "✅" if collected else "❌"
                status.append(f"{emoji} {rarity.title()}")

            embed.add_field(
                name=f"{type_data['emoji']} {type_data['name']}",
                value="\n".join(status),
                inline=True
            )

        rewards = {
            25: "🥉 Bronze Collector: +5% coin rewards",
            50: "🥈 Silver Collector: +10% coin rewards",
            75: "🥇 Gold Collector: +15% coin rewards",
            100: "👑 Master Collector: +25% coin rewards"
        }

        achieved_rewards = []
        for threshold, reward in rewards.items():
            if completion_percent >= threshold:
                achieved_rewards.append(reward)

        if achieved_rewards:
            embed.add_field(
                name="🏆 Collection Rewards",
                value="\n".join(achieved_rewards),
                inline=False
            )

        await ctx.send(embed=embed)

    @pet.command(name="trade")
    @is_econ_allowed()
    async def pet_trade(self, ctx: Context, user: Member, your_pet: str, their_pet: str):
        """Trade pets with another user"""
        if user.bot or user == ctx.author:
            return await ctx.warn("You can't trade with that user!")

        trade_fee = 10000  
        wallet, _, _ = await self.get_balance(ctx.author.id)
        
        if wallet < trade_fee:
            return await ctx.warn(f"You need {trade_fee:,} coins for the trading fee!")
            
        other_wallet, _, _ = await self.get_balance(user.id)
        if other_wallet < trade_fee:
            return await ctx.warn(f"{user.name} doesn't have enough coins for the trading fee!")

        async with self.bot.db.acquire() as conn:
            your_pet_data = await conn.fetchrow(
                """SELECT * FROM pets 
                WHERE owner_id = $1 AND LOWER(name) = LOWER($2)""",
                ctx.author.id, your_pet
            )
            
            their_pet_data = await conn.fetchrow(
                """SELECT * FROM pets 
                WHERE owner_id = $1 AND LOWER(name) = LOWER($2)""",
                user.id, their_pet
            )

            if not your_pet_data:
                return await ctx.warn("Your pet not found!")
                
            if not their_pet_data:
                return await ctx.warn("Their pet not found!")

            active_adventure = await conn.fetchrow(
                """SELECT 1 FROM pet_adventures 
                WHERE pet_id IN ($1, $2) AND completed = false""",
                your_pet_data["pet_id"], their_pet_data["pet_id"]
            )
            
            if active_adventure:
                return await ctx.warn("One or both pets are currently on an adventure!")

            if your_pet_data["active"] or their_pet_data["active"]:
                return await ctx.warn("Cannot trade active pets! Use `pet active` to change active pets first.")

            embed = Embed(
                title="🤝 Pet Trade Request",
                description=(
                    f"**{ctx.author.name}** wants to trade:\n"
                    f"Their {self.pet_types[your_pet_data['type']]['emoji']} "
                    f"**{your_pet_data['name']}** "
                    f"({your_pet_data['rarity'].title()} • Level {your_pet_data['level']})\n\n"
                    f"For {user.name}'s {self.pet_types[their_pet_data['type']]['emoji']} "
                    f"**{their_pet_data['name']}** "
                    f"({their_pet_data['rarity'].title()} • Level {their_pet_data['level']})\n\n"
                    f"Trading fee: {trade_fee:,} coins each"
                ),
                color=discord.Color.blue()
            )

            class TradeView(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=60.0)
                    self.value = None

                @discord.ui.button(label="Accept Trade", style=discord.ButtonStyle.green)
                async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
                    if interaction.user.id != user.id:
                        return
                    self.value = True
                    self.stop()

                @discord.ui.button(label="Decline Trade", style=discord.ButtonStyle.red)
                async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
                    if interaction.user.id != user.id:
                        return
                    self.value = False
                    self.stop()

            view = TradeView()
            trade_msg = await ctx.send(embed=embed, view=view)
            await view.wait()

            if view.value is None:
                await trade_msg.edit(content="Trade request timed out!", embed=None, view=None)
                return
                
            if not view.value:
                await trade_msg.edit(content="Trade declined!", embed=None, view=None)
                return

            async with conn.transaction():
                await conn.execute(
                    """UPDATE pets 
                    SET owner_id = $1, name = $2 
                    WHERE pet_id = $3""",
                    user.id, their_pet_data["name"], your_pet_data["pet_id"]
                )
                
                await conn.execute(
                    """UPDATE pets 
                    SET owner_id = $1, name = $2 
                    WHERE pet_id = $3""",
                    ctx.author.id, your_pet_data["name"], their_pet_data["pet_id"]
                )

                await conn.execute(
                    """UPDATE economy 
                    SET wallet = wallet - $1 
                    WHERE user_id = $2""",
                    trade_fee, ctx.author.id
                )
                
                await conn.execute(
                    """UPDATE economy 
                    SET wallet = wallet - $1 
                    WHERE user_id = $2""",
                    trade_fee, user.id
                )

                await conn.execute(
                    """INSERT INTO pet_trades (
                        pet1_id, pet2_id, 
                        user1_id, user2_id, 
                        trade_fee
                    ) VALUES ($1, $2, $3, $4, $5)""",
                    your_pet_data["pet_id"], their_pet_data["pet_id"],
                    ctx.author.id, user.id,
                    trade_fee
                )

            success_embed = Embed(
                title="🤝 Trade Complete!",
                description=(
                    f"**{ctx.author.name}** received {self.pet_types[their_pet_data['type']]['emoji']} "
                    f"**{their_pet_data['name']}**\n"
                    f"**{user.name}** received {self.pet_types[your_pet_data['type']]['emoji']} "
                    f"**{your_pet_data['name']}**\n\n"
                    f"Trading fee: {trade_fee:,} coins each"
                ),
                color=discord.Color.green()
            )
            await trade_msg.edit(embed=success_embed, view=None)

    @pet.command(name="trades")
    @is_econ_allowed()
    async def pet_trades(self, ctx: Context):
        """View your recent pet trades"""
        async with self.bot.db.acquire() as conn:
            trades = await conn.fetch(
                """SELECT * FROM pet_trades 
                WHERE user1_id = $1 OR user2_id = $1 
                ORDER BY trade_time DESC LIMIT 10""",
                ctx.author.id
            )

            if not trades:
                return await ctx.warn("You haven't made any trades yet!")

            embed = Embed(
                title="📜 Recent Pet Trades",
                color=discord.Color.blue()
            )

            for trade in trades:
                pet1 = await conn.fetchrow(
                    "SELECT name, type, rarity FROM pets WHERE pet_id = $1",
                    trade["pet1_id"]
                )
                pet2 = await conn.fetchrow(
                    "SELECT name, type, rarity FROM pets WHERE pet_id = $1",
                    trade["pet2_id"]
                )

                user1 = ctx.guild.get_member(trade["user1_id"])
                user2 = ctx.guild.get_member(trade["user2_id"])
                
                user1_name = user1.name if user1 else "Unknown"
                user2_name = user2.name if user2 else "Unknown"

                trade_time = trade["trade_time"].strftime("%Y-%m-%d %H:%M")
                
                embed.add_field(
                    name=f"Trade on {trade_time}",
                    value=(
                        f"{user1_name}: {self.pet_types[pet1['type']]['emoji']} "
                        f"**{pet1['name']}** ({pet1['rarity'].title()})\n"
                        f"{user2_name}: {self.pet_types[pet2['type']]['emoji']} "
                        f"**{pet2['name']}** ({pet2['rarity'].title()})\n"
                        f"Fee: {trade['trade_fee']:,} coins"
                    ),
                    inline=False
                )

            await ctx.send(embed=embed)

class PetBattle:
    def __init__(self, ctx, opponent, challenger_pet, opponent_pet, bet):
        self.ctx = ctx
        self.opponent = opponent
        self.challenger_pet = challenger_pet
        self.opponent_pet = opponent_pet
        self.bet = bet
        self.current_turn = ctx.author
        self.round = 1
        
    async def start_battle(self, msg):
        """Start and manage the battle"""
        challenger_hp = 100
        opponent_hp = 100
        
        while challenger_hp > 0 and opponent_hp > 0:
            embed = self.create_battle_embed(challenger_hp, opponent_hp)
            
            moves = {
                "⚔️": {"name": "Attack", "dmg": (15, 25), "accuracy": 0.9},
                "🛡️": {"name": "Block", "block": (10, 20), "counter": (5, 10)},
                "🎯": {"name": "Precise Strike", "dmg": (25, 35), "accuracy": 0.7},
                "💫": {"name": "Special Move", "dmg": (35, 50), "accuracy": 0.5}
            }
            
            class MoveView(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=30.0)
                    self.value = None

                @discord.ui.button(emoji="⚔️", style=discord.ButtonStyle.gray)
                async def attack(self, interaction: discord.Interaction, button: discord.ui.Button):
                    self.value = "⚔️"
                    self.stop()

                @discord.ui.button(emoji="🛡️", style=discord.ButtonStyle.gray)
                async def block(self, interaction: discord.Interaction, button: discord.ui.Button):
                    self.value = "🛡️"
                    self.stop()

                @discord.ui.button(emoji="🎯", style=discord.ButtonStyle.gray)
                async def precise(self, interaction: discord.Interaction, button: discord.ui.Button):
                    self.value = "🎯"
                    self.stop()

                @discord.ui.button(emoji="💫", style=discord.ButtonStyle.gray)
                async def special(self, interaction: discord.Interaction, button: discord.ui.Button):
                    self.value = "💫"
                    self.stop()

            view = MoveView()
            await msg.edit(embed=embed, view=view)
            await view.wait()

            if view.value is None:
                await msg.edit(content="Battle cancelled due to inactivity!", embed=None, view=None)
                return

            move = moves[view.value]
            
            if random.random() <= move["accuracy"]:
                if "dmg" in move:
                    damage = random.randint(*move["dmg"])
                    if self.current_turn == self.ctx.author:
                        opponent_hp -= damage
                    else:
                        challenger_hp -= damage
            
            self.current_turn = self.opponent if self.current_turn == self.ctx.author else self.ctx.author
            self.round += 1

        winner = self.ctx.author if opponent_hp <= 0 else self.opponent
        loser = self.opponent if winner == self.ctx.author else self.ctx.author
        
        if self.bet > 0:
            async with self.ctx.bot.db.acquire() as conn:
                async with conn.transaction():
                    await conn.execute(
                        """UPDATE economy 
                        SET wallet = wallet + $1 
                        WHERE user_id = $2""",
                        self.bet, winner.id
                    )
                    await conn.execute(
                        """UPDATE economy 
                        SET wallet = wallet - $1 
                        WHERE user_id = $2""",
                        self.bet, loser.id
                    )

        embed = Embed(
            title="🏆 Battle Ended!",
            description=(
                f"**Winner:** {winner.mention}\n"
                f"Remaining HP: {max(challenger_hp, opponent_hp):,.0f}\n"
                f"Rounds: {self.round}\n"
                f"Prize: {self.bet:,} coins" if self.bet > 0 else ""
            ),
            color=discord.Color.green()
        )
        await msg.edit(embed=embed, view=None)

    def create_battle_embed(self, challenger_hp, opponent_hp):
        """Create the battle status embed"""
        return Embed(
            title="⚔️ Pet Battle",
            description=(
                f"Round {self.round}\n"
                f"Current turn: {self.current_turn.mention}\n\n"
                f"{self.ctx.author.name}'s {self.challenger_pet['name']}: {challenger_hp:,.0f} HP\n"
                f"{self.opponent.name}'s {self.opponent_pet['name']}: {opponent_hp:,.0f} HP"
            ),
            color=discord.Color.orange()
        )

class BlackjackGame:
    def __init__(self, ctx, bet, bet_type, economy_cog):
        self.ctx = ctx
        self.bet = bet
        self.bet_type = bet_type
        self.economy_cog = economy_cog
        self.game_id = str(uuid.uuid4())
        self.players = []
        self.dealer_hand = []
        self.current_player_index = 0
        self.game_status = "joining"
        self.game_message = None
        self.action_message = None
        self.suits = {"hearts": "♥️", "diamonds": "♦️", "clubs": "♣️", "spades": "♠️"}
        self.values = {
            "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "10": 10,
            "J": 10, "Q": 10, "K": 10, "A": 1
        }
        self.deck = []

    async def offer_insurance(self):
        """Offer insurance to all players"""
        embed = Embed(
            title="🎰 Insurance Betting",
            description=(
                "Dealer shows an Ace! You can bet insurance.\n"
                "Type `insurance` to place an insurance bet (half your original bet).\n"
                "Insurance pays 2:1 if dealer has blackjack.\n"
                "You have 15 seconds to decide."
            ),
            color=discord.Color.gold()
        )
        await self.ctx.send(embed=embed)

        def check(m):
            return (
                m.channel == self.ctx.channel and
                m.content.lower() == "insurance" and
                any(p["user"].id == m.author.id for p in self.players)
            )

        try:
            while True:
                msg = await self.ctx.bot.wait_for('message', timeout=15.0, check=check)
                player = next(p for p in self.players if p["user"].id == msg.author.id)
                
                if player["insurance"] == 0:
                    insurance_amount = player["bet"] // 2
                    wallet, _, _ = await self.economy_cog.get_balance(player["user"].id)
                    
                    if wallet >= insurance_amount:
                        player["insurance"] = insurance_amount
                        await self.ctx.approve(f"{player['user'].name} placed insurance bet of {insurance_amount:,} coins")
                    else:
                        await self.ctx.warn(f"{player['user'].name} doesn't have enough coins for insurance!")
        except asyncio.TimeoutError:
            pass

        if self.calculate_hand(self.dealer_hand) == 21:
            self.game_status = "ended"
            await self.handle_insurance_payouts()
            await self.end_game()

    def create_deck(self):
        """Create and shuffle a new deck of cards"""
        cards = []
        for suit in self.suits:
            for value in self.values:
                cards.append({"suit": suit, "value": value})
        random.shuffle(cards)
        self.deck = cards

    def draw_card(self):
        """Draw a card from the deck"""
        return self.deck.pop()

    def format_card(self, card):
        """Format a card for display"""
        return f"{self.suits[card['suit']]}{card['value']}"

    def format_hand(self, hand, hide_second=False):
        """Format a hand of cards for display"""
        if hide_second and len(hand) > 1:
            return f"{self.format_card(hand[0])} 🂠"
        return " ".join(self.format_card(card) for card in hand)

    async def handle_action(self, action: str):
        """Handle player action from reaction"""
        current_player = self.players[self.current_player_index]
        
        if action == "hit":
            current_player["hand"].append(self.draw_card())
            hand_value = self.calculate_hand(current_player["hand"])
            
            if hand_value > 21:
                current_player["status"] = "Bust"
                await self.next_turn()
            await self.update_game_message()

        elif action == "stand":
            current_player["status"] = "Stand"
            await self.next_turn()

        elif action == "double" and await self.can_double_down(current_player):
            current_player["bet"] *= 2
            current_player["hand"].append(self.draw_card())
            hand_value = self.calculate_hand(current_player["hand"])
            
            if hand_value > 21:
                current_player["status"] = "Bust"
            else:
                current_player["status"] = "Double Down"
            await self.next_turn()

        elif action == "split" and await self.can_split(current_player):
            new_hand = [current_player["hand"].pop()]
            self.players.insert(self.current_player_index + 1, {
                "user": current_player["user"],
                "bet": current_player["bet"],
                "hand": [new_hand[0]],
                "status": "Playing",
                "split": True
            })
            
            current_player["hand"].append(self.draw_card())
            self.players[self.current_player_index + 1]["hand"].append(self.draw_card())
            await self.update_game_message()

    async def can_double_down(self, player):
        """Check if player can double down (only on first turn with 2 cards)"""
        wallet, _, _ = await self.economy_cog.get_balance(player["user"].id)
        return (
            len(player["hand"]) == 2 and
            wallet >= player["bet"] and
            not player.get("split") 
        )

    async def can_split(self, player):
        """Check if player can split their hand"""
        wallet, _, _ = await self.economy_cog.get_balance(player["user"].id)
        hand = player["hand"]
        return (
            len(hand) == 2 and
            hand[0]["value"] == hand[1]["value"] and
            wallet >= player["bet"] and
            not player.get("split")  
        )

    async def can_insurance(self, player):
        """Check if player can take insurance"""
        wallet, _, _ = await self.economy_cog.get_balance(player["user"].id)
        return (
            self.dealer_hand[0]["value"] == "A" and
            wallet >= (player["bet"] // 2) and
            player["insurance"] == 0
        )

    def calculate_hand(self, hand):
        value = 0
        aces = 0
        
        for card in hand:
            card_value = card["value"]
            if card_value == "A":
                aces += 1
            else:
                value += self.values[card_value]
        
        for _ in range(aces):
            if value + 11 <= 21:
                value += 11
            else:
                value += 1
                
        return value

    async def start_game(self):
        self.create_deck()
        
        self.dealer_hand = [self.draw_card(), self.draw_card()]
        for player in self.players:
            player["hand"] = [self.draw_card(), self.draw_card()]
            player["status"] = "Playing"

        self.game_status = "playing"
        await self.update_game_message()

    async def next_turn(self):
        self.current_player_index += 1
        
        if self.current_player_index >= len(self.players):
            await self.dealer_turn()
        else:
            await self.update_game_message()

    async def dealer_turn(self):
        self.game_status = "ended"
        dealer_value = self.calculate_hand(self.dealer_hand)
        
        while dealer_value < 17:
            self.dealer_hand.append(self.draw_card())
            dealer_value = self.calculate_hand(self.dealer_hand)

        await self.end_game()

    async def end_game(self):
        dealer_value = self.calculate_hand(self.dealer_hand)
        dealer_bust = dealer_value > 21

        async with self.ctx.bot.db.acquire() as conn:
            async with conn.transaction():
                for player in self.players:
                    hand_value = self.calculate_hand(player["hand"])
                    
                    if hand_value > 21:
                        player["status"] = "Lost"
                        await conn.execute(
                            """UPDATE economy 
                            SET wallet = wallet - $1 
                            WHERE user_id = $2""",
                            player["bet"], player["user"].id
                        )
                    elif dealer_bust or hand_value > dealer_value:
                        player["status"] = "Won"
                        await conn.execute(
                            """UPDATE economy 
                            SET wallet = wallet + $1 
                            WHERE user_id = $2""",
                            player["bet"], player["user"].id
                        )
                    elif hand_value < dealer_value:
                        player["status"] = "Lost"
                        await conn.execute(
                            """UPDATE economy 
                            SET wallet = wallet - $1 
                            WHERE user_id = $2""",
                            player["bet"], player["user"].id
                        )
                    else:
                        player["status"] = "Push"

        await self.update_game_message()

    async def update_game_message(self):
        """Update the game state message"""
        embed = Embed(title="🎰 Blackjack Game", color=discord.Color.gold())
        
        if self.dealer_hand:
            dealer_value = "?" if self.game_status == "playing" else self.calculate_hand(self.dealer_hand)
            embed.add_field(
                name="Dealer's Hand",
                value=(
                    f"{self.format_hand(self.dealer_hand, self.game_status == 'playing')}\n"
                    f"Value: {dealer_value}"
                ),
                inline=False
            )

        for i, player in enumerate(self.players):
            current = i == self.current_player_index and self.game_status == "playing"
            status = "🎮 Your Turn" if current else player["status"]
            hand_value = self.calculate_hand(player["hand"])
            
            split_indicator = " (Split)" if player.get("split") else ""
            embed.add_field(
                name=f"{player['user'].name}'s Hand{split_indicator} ({player['bet']:,} coins)",
                value=(
                    f"{self.format_hand(player['hand'])}\n"
                    f"Value: {hand_value}\n"
                    f"Status: {status}"
                ),
                inline=False
            )

        if self.game_message:
            await self.game_message.edit(embed=embed)
        else:
            self.game_message = await self.ctx.send(embed=embed)

    @tasks.loop(minutes=1)
    async def check_lottery(self):
        """Check if lottery should be drawn"""
        next_draw = await self.bot.redis.get("lottery:next_draw")
        if not next_draw:
            return
            
        next_draw = datetime.fromtimestamp(float(next_draw), timezone.utc)
        if datetime.now(timezone.utc) >= next_draw:
            await self.draw_lottery()

    async def draw_lottery(self):
        """Draw the lottery and reward winner"""
        total_tickets = await self.bot.redis.get("lottery:total_tickets")
        if not total_tickets or int(total_tickets) == 0:
            pipe = self.bot.redis.pipeline()
            pipe.delete("lottery:total_tickets", "lottery:pot")
            next_draw = datetime.now(timezone.utc) + timedelta(days=1)
            pipe.set("lottery:next_draw", next_draw.timestamp())
            await pipe.execute()
            return
            
        total_tickets = int(total_tickets)
        winning_ticket = random.randint(1, total_tickets)
        pot = int(await self.bot.redis.get("lottery:pot") or 0)
        
        current_count = 0
        async for key in self.bot.redis.scan_iter("lottery:tickets:*"):
            user_tickets = int(await self.bot.redis.get(key))
            current_count += user_tickets
            
            if current_count >= winning_ticket:
                winner_id = int(key.split(":")[-1])
                
                async with self.bot.db.acquire() as conn:
                    async with conn.transaction():
                        await conn.execute(
                            """UPDATE economy 
                            SET wallet = wallet + $1 
                            WHERE user_id = $2""",
                            pot, winner_id
                        )
                        
                        await conn.execute(
                            """INSERT INTO lottery_history 
                            (user_id, pot_amount, total_tickets, winner_tickets, won_at)
                            VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)""",
                            winner_id, pot, total_tickets, user_tickets
                        )
                
                channel = self.bot.get_channel(1319467099969556542)
                if channel:
                    winner = self.bot.get_user(winner_id)
                    if winner:
                        embed = Embed(
                            title="🎰 Lottery Winner!",
                            description=(
                                f"Congratulations to {winner.mention}!\n"
                                f"They won {pot:,} coins with {user_tickets:,} tickets!\n"
                                f"Winning chance was {(user_tickets/total_tickets)*100:.2f}%"
                            ),
                            color=discord.Color.gold()
                        )
                        await channel.send(embed=embed)
                break
                
        pipe = self.bot.redis.pipeline()
        pipe.delete("lottery:total_tickets", "lottery:pot")
        next_draw = datetime.now(timezone.utc) + timedelta(days=1)
        pipe.set("lottery:next_draw", next_draw.timestamp())
        await pipe.execute()
        
        async for key in self.bot.redis.scan_iter("lottery:tickets:*"):
            await self.bot.redis.delete(key)

class DuelGame:
    def __init__(self, challenger, opponent, amount):
        self.challenger = challenger
        self.opponent = opponent
        self.amount = amount
        self.challenger_hp = 100
        self.opponent_hp = 100
        self.current_turn = challenger
        self.moves = {
            "⚔️": {"name": "Attack", "dmg": (15, 25), "accuracy": 0.9},
            "🛡️": {"name": "Block", "block": (10, 20), "counter": (5, 10)},
            "🎯": {"name": "Precise Strike", "dmg": (25, 35), "accuracy": 0.7},
            "💫": {"name": "Special Move", "dmg": (35, 50), "accuracy": 0.5}
        }
        self.last_move = None
        self.blocked = False

class DuelView(discord.ui.View):
    def __init__(self, game):
        super().__init__(timeout=30.0)
        self.game = game
        self.value = None

    @discord.ui.button(label="Attack", emoji="⚔️", style=discord.ButtonStyle.danger)
    async def attack(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_move(interaction, "⚔️")

    @discord.ui.button(label="Block", emoji="🛡️", style=discord.ButtonStyle.primary)
    async def block(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_move(interaction, "🛡️")

    @discord.ui.button(label="Precise", emoji="🎯", style=discord.ButtonStyle.success)
    async def precise(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_move(interaction, "🎯")

    @discord.ui.button(label="Special", emoji="💫", style=discord.ButtonStyle.secondary)
    async def special(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_move(interaction, "💫")

    async def handle_move(self, interaction: discord.Interaction, move):
        if interaction.user.id != self.game.current_turn.id:
            return await interaction.response.send_message("It's not your turn!", ephemeral=True)
        
        await interaction.response.defer()
        
        move_data = self.game.moves[move]
        self.game.blocked = False
        damage = 0
        message = ""

        if self.game.last_move == "🛡️" and move != "🛡️":
            damage = int(random.randint(*move_data["dmg"]) * 0.5)
            message += "🛡️ Damage reduced by block!\n"
        elif move == "🛡️":
            self.game.blocked = True
            block_amount = random.randint(*move_data["block"])
            counter = random.randint(*move_data["counter"])
            message += f"🛡️ Blocked {block_amount} damage and countered for {counter} damage!\n"
            
            if self.game.current_turn == self.game.challenger:
                self.game.opponent_hp -= counter
            else:
                self.game.challenger_hp -= counter
        else:
            if random.random() <= move_data["accuracy"]:
                damage = random.randint(*move_data["dmg"])
                message += f"{move} {move_data['name']} hit for {damage} damage!\n"
            else:
                message += f"{move} {move_data['name']} missed!\n"

        if self.game.current_turn == self.game.challenger:
            self.game.opponent_hp -= damage
            self.game.current_turn = self.game.opponent
        else:
            self.game.challenger_hp -= damage
            self.game.current_turn = self.game.challenger

        self.game.last_move = move

        embed = Embed(
            title="⚔️ Coin Duel",
            description=(
                f"{message}\n"
                f"{self.game.challenger.name}: ❤️ {max(0, self.game.challenger_hp)}/100\n"
                f"{self.game.opponent.name}: ❤️ {max(0, self.game.opponent_hp)}/100\n\n"
                f"Current turn: {self.game.current_turn.mention}"
            ),
            color=discord.Color.gold()
        )

        await interaction.message.edit(embed=embed)

        if self.game.challenger_hp <= 0 or self.game.opponent_hp <= 0:
            winner = self.game.opponent if self.game.challenger_hp <= 0 else self.game.opponent
            loser = self.game.challenger if winner == self.game.opponent else self.game.challenger
            
            embed.description = (
                f"**{winner.name}** wins the duel!\n"
                f"They won **{self.game.amount:,}** coins from {loser.name}!"
            )
            self.value = winner
            self.stop()