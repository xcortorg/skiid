import datetime
import random
import time
from datetime import datetime, timedelta

import asyncpg
import discord
from discord.ext import commands
from tools.config import color
from tools.context import Context


class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool = bot.pool

    async def get_last_daily(self, user_id):
        """Fetch the last time the daily reward was claimed for a user."""
        async with self.pool.acquire() as connection:
            return await connection.fetchval(
                "SELECT last_daily FROM economy WHERE user_id = $1", user_id
            )

    async def set_last_daily(self, user_id, timestamp):
        """Set the last time the daily reward was claimed for a user."""
        async with self.pool.acquire() as connection:
            await connection.execute(
                "INSERT INTO economy (user_id, last_daily) VALUES ($1, $2) "
                "ON CONFLICT (user_id) DO UPDATE SET last_daily = $2",
                user_id,
                timestamp,
            )

    async def get_cooldown(self, user_id):
        """Fetch the last command timestamp for the user."""
        if not self.pool:
            raise Exception("Database connection pool has not been initialized.")
        async with self.pool.acquire() as connection:
            return await connection.fetchval(
                "SELECT last_command_timestamp FROM cooldowns WHERE user_id = $1",
                user_id,
            )

    async def set_cooldown(self, user_id, timestamp):
        """Set the last command timestamp for the user."""
        async with self.pool.acquire() as connection:
            await connection.execute(
                "INSERT INTO cooldowns (user_id, last_command_timestamp) VALUES ($1, $2) "
                "ON CONFLICT (user_id) DO UPDATE SET last_command_timestamp = $2",
                user_id,
                timestamp,
            )

    async def get_last_claim(self, user_id, claim_type):
        """Fetch the last claim time for a specific claim type."""
        if not self.pool:
            raise Exception("Database connection pool has not been initialized.")
        async with self.pool.acquire() as connection:
            result = await connection.fetchrow(
                f"SELECT last_{claim_type} FROM economy WHERE user_id = $1", user_id
            )
            return result[f"last_{claim_type}"] if result else None

    async def set_last_claim(self, user_id, claim_type, current_time):
        """Set the last claim time for a specific claim type."""
        if not self.pool:
            raise Exception("Database connection pool has not been initialized.")
        async with self.pool.acquire() as connection:
            await connection.execute(
                f"INSERT INTO economy (user_id, last_{claim_type}) VALUES ($1, $2) "
                f"ON CONFLICT (user_id) DO UPDATE SET last_{claim_type} = $2",
                user_id,
                current_time,
            )

    async def get_balance(self, user_id, connection=None):
        """Fetch the balance for a user."""
        if not self.pool:
            raise Exception("Database connection pool has not been initialized.")
        if connection:
            result = await connection.fetchrow(
                "SELECT balance FROM economy WHERE user_id = $1", user_id
            )
        else:
            async with self.pool.acquire() as conn:
                result = await conn.fetchrow(
                    "SELECT balance FROM economy WHERE user_id = $1", user_id
                )
        return result["balance"] if result else 0

    @commands.command(name="balance", aliases=["bal"])
    async def balance(self, ctx: Context, member: discord.Member = None):
        """Check your balance or another user's balance."""
        member = member or ctx.author
        try:
            balance = await self.get_balance(member.id)
            await ctx.agree(f"{member.display_name}'s balance is: **${balance}**")
        except Exception as e:
            print(f"Error in balance command: {e}")
            await ctx.deny("An error occurred while retrieving the balance.")

    @commands.command(name="work", aliases=["earn"])
    async def work(self, ctx: Context):
        """Earn some money by working."""
        earnings = random.randint(5, 150)
        cooldown_duration = 15

        last_work = await self.get_cooldown(ctx.author.id)
        current_time = time.time()

        if last_work is not None and current_time - last_work < cooldown_duration:
            remaining = cooldown_duration - (current_time - last_work)
            await ctx.deny(
                f"You need to wait {int(remaining)} seconds before using this command again."
            )
            return

        async with self.pool.acquire() as connection:
            try:
                async with connection.transaction():
                    await connection.execute(
                        "UPDATE economy SET balance = balance + $1 WHERE user_id = $2",
                        earnings,
                        ctx.author.id,
                    )
                await self.set_cooldown(ctx.author.id, current_time)
                await ctx.agree(f"You worked hard and earned **${earnings}**!")
            except Exception as e:
                print(f"Error in work command: {e}")
                await ctx.deny("An error occurred while trying to work.")

    @commands.command(name="pay", aliases=["send"])
    async def pay(self, ctx: Context, member: discord.Member, amount: int):
        """Pay another user some money."""
        if amount <= 0:
            await ctx.deny("You cannot pay a negative amount or zero.")
            return

        async with self.pool.acquire() as connection:
            try:
                async with connection.transaction():
                    sender_balance = await self.get_balance(connection, ctx.author.id)

                    if sender_balance < amount:
                        await ctx.deny(
                            "You don't have enough money to make this payment."
                        )
                        return

                    await connection.execute(
                        "UPDATE economy SET balance = balance - $1 WHERE user_id = $2",
                        amount,
                        ctx.author.id,
                    )

                    await connection.execute(
                        "UPDATE economy SET balance = balance + $1 WHERE user_id = $2",
                        amount,
                        member.id,
                    )

                await ctx.agree(f"You paid {member.mention} **${amount}**!")
            except Exception as e:
                print(f"Error in pay command: {e}")
                await ctx.deny("An error occurred during the payment process.")

    @commands.command(name="leaderboard", aliases=["lb"])
    async def leaderboard(self, ctx: Context):
        """View the global economy leaderboard."""
        try:
            async with self.pool.acquire() as connection:
                leaderboard = await connection.fetch(
                    "SELECT user_id, balance FROM economy ORDER BY balance DESC LIMIT 10"
                )

                if not leaderboard:
                    await ctx.deny("No users have a balance yet.")
                    return

                embed = discord.Embed(
                    title="Global Economy Leaderboard", color=color.default
                )

                for rank, row in enumerate(leaderboard, start=1):
                    user_id = row["user_id"]
                    balance = row["balance"]
                    user = self.bot.get_user(user_id) or "Unknown User"
                    embed.add_field(
                        name=f"{rank}. {user}", value=f"**${balance}**", inline=False
                    )

                await ctx.send(embed=embed)

        except Exception as e:
            print(f"Error in leaderboard command: {e}")
            await ctx.deny("An error occurred while fetching the leaderboard.")

    @commands.command(aliases=["cfp"])
    async def cflip(self, ctx: Context):
        """Flip a coin and gamble some money."""
        bet = 100
        cooldown_duration = 10

        last_coinflip = await self.get_cooldown(ctx.author.id)

        if (
            last_coinflip is not None
            and time.time() - last_coinflip < cooldown_duration
        ):
            remaining = cooldown_duration - (time.time() - last_coinflip)
            await ctx.deny(
                f"You need to wait {int(remaining)} seconds before using this command again."
            )
            return

        result = random.choice(["Heads", "Tails"])
        outcome = random.choice(["Win", "Lose"])
        winnings = bet if outcome == "Win" else -bet

        async with self.pool.acquire() as connection:
            try:
                async with connection.transaction():
                    user_balance = await self.get_balance(ctx.author.id, connection)
                    if user_balance + winnings < 0:
                        await ctx.deny("You don't have enough money to gamble.")
                        return

                    await connection.execute(
                        "UPDATE economy SET balance = balance + $1 WHERE user_id = $2",
                        winnings,
                        ctx.author.id,
                    )

                await self.set_cooldown(ctx.author.id, time.time())
                await ctx.agree(
                    f"The coin landed on **{result}**! You {'won' if outcome == 'Win' else 'lost'} and now have **${user_balance + winnings}**!"
                )
            except Exception as e:
                print(f"Error in coinflip command: {e}")
                await ctx.deny("An error occurred during the coin flip.")

    @commands.command(aliases=["gmb"])
    async def gamble(self, ctx: Context, amount: int):
        """Gamble a specified amount of money."""
        if amount <= 0:
            await ctx.deny("You cannot gamble a negative amount or zero.")
            return

        cooldown_duration = 5

        last_gamble = await self.get_cooldown(ctx.author.id)
        current_time = time.time()

        if last_gamble is not None and current_time - last_gamble < cooldown_duration:
            remaining = cooldown_duration - (current_time - last_gamble)
            await ctx.deny(
                f"You need to wait {int(remaining)} seconds before using this command again."
            )
            return

        async with self.pool.acquire() as connection:
            try:
                async with connection.transaction():
                    user_balance = await self.get_balance(ctx.author.id, connection)
                    if user_balance < amount:
                        await ctx.deny("You don't have enough money to gamble.")
                        return

                    result = random.choice(["Win", "Lose"])
                    winnings = amount if result == "Win" else -amount
                    new_balance = user_balance + winnings

                    await connection.execute(
                        "UPDATE economy SET balance = balance + $1 WHERE user_id = $2",
                        winnings,
                        ctx.author.id,
                    )

                await self.set_cooldown(ctx.author.id, current_time)

                outcome_message = f"You gambled **${amount}** and {'won' if result == 'Win' else 'lost'}. Your new balance is **${new_balance}**."
                if result == "Win":
                    await ctx.agree(outcome_message)
                else:
                    await ctx.deny(outcome_message)

            except Exception as e:
                print(f"Error in gamble command: {e}")
                await ctx.deny("An error occurred during the gambling process.")

    @commands.command(name="rob")
    async def rob(self, ctx: Context, member: discord.Member):
        """Attempt to steal money from another player."""
        if member == ctx.author:
            await ctx.deny("You cannot rob yourself!")
            return

        target_balance = await self.get_balance(member.id)
        if target_balance <= 0:
            await ctx.deny(f"{member.display_name} has no money to rob.")
            return

        success = random.choice([True, False])
        if success:
            amount_to_steal = random.randint(1, target_balance)
            await self.update_balance(ctx.author.id, amount_to_steal)
            await self.update_balance(member.id, -amount_to_steal)
            await ctx.agree(
                f"You successfully robbed **${amount_to_steal}** from {member.display_name}!"
            )
        else:
            await ctx.deny(f"You attempted to rob {member.display_name} but failed!")

    @commands.command(name="daily")
    async def daily(self, ctx: Context):
        """Claim your daily reward."""
        reward_amount = 500
        current_time = datetime.utcnow()

        try:
            last_daily = await self.get_last_daily(ctx.author.id)

            if last_daily:
                time_difference = current_time - last_daily

                if time_difference < timedelta(days=1):
                    remaining = timedelta(days=1) - time_difference
                    remaining_hours = remaining.seconds // 3600
                    remaining_seconds = remaining.seconds % 3600

                    await ctx.deny(
                        f"You need to wait **{remaining_hours} hours and {remaining_seconds} seconds** before claiming your daily reward again."
                    )
                    return

            async with self.pool.acquire() as connection:
                async with connection.transaction():
                    await connection.execute(
                        "UPDATE economy SET balance = balance + $1 WHERE user_id = $2",
                        reward_amount,
                        ctx.author.id,
                    )
                    await self.set_last_daily(ctx.author.id, current_time)

                await ctx.agree(
                    f"You claimed your daily reward of **${reward_amount}**!"
                )
        except Exception as e:
            print(f"Error in daily command: {e}")
            await ctx.deny("An error occurred while claiming your daily reward.")

    @commands.command(name="beg")
    async def beg(self, ctx: Context):
        """Beg for some money."""
        amount = random.randint(1, 50)
        cooldown_duration = 15
        last_beg = await self.get_cooldown(ctx.author.id)
        if last_beg is None:
            await self.set_cooldown(ctx.author.id, time.time())
        else:
            if time.time() - last_beg < cooldown_duration:
                remaining = cooldown_duration - (time.time() - last_beg)
                await ctx.deny(
                    f"You need to wait {int(remaining)} seconds before begging again."
                )
                return
        async with self.pool.acquire() as connection:
            try:
                async with connection.transaction():
                    await connection.execute(
                        "UPDATE economy SET balance = balance + $1 WHERE user_id = $2",
                        amount,
                        ctx.author.id,
                    )
                    await self.set_cooldown(ctx.author.id, time.time())
                await ctx.agree(f"You begged and received **${amount}**!")
            except Exception as e:
                print(f"Error in beg command: {e}")
                await ctx.deny("An error occurred while begging.")

    @commands.command(name="slut")
    async def slut(self, ctx: Context):
        """Work as a prostitute for money."""
        earnings = random.randint(50, 500)
        current_time = datetime.utcnow()

        try:
            async with self.pool.acquire() as connection:
                async with connection.transaction():
                    await connection.execute(
                        "UPDATE economy SET balance = balance + $1 WHERE user_id = $2",
                        earnings,
                        ctx.author.id,
                    )

            await ctx.agree(f"You worked as a prostitute and earned **${earnings}**!")
        except Exception as e:
            print(f"Error in slut command: {e}")
            await ctx.deny("An error occurred while trying to earn money.")

    @commands.command(name="blackjack")
    async def blackjack(self, ctx: Context, bet: int):
        """Play blackjack with a specified bet amount."""
        if bet <= 0:
            await ctx.deny("You cannot bet a negative amount or zero.")
            return

        async with self.pool.acquire() as connection:
            try:
                user_balance = await self.get_balance(ctx.author.id)
                if user_balance < bet:
                    await ctx.deny("You don't have enough money to play blackjack.")
                    return

                player_hand = [random.randint(1, 11), random.randint(1, 11)]
                dealer_hand = [random.randint(1, 11), random.randint(1, 11)]

                player_total = sum(player_hand)
                dealer_total = sum(dealer_hand)

                if player_total > 21:
                    await ctx.deny(
                        f"You bust with a total of **{player_total}**! You lost **${bet}**."
                    )
                    await connection.execute(
                        "UPDATE economy SET balance = balance - $1 WHERE user_id = $2",
                        bet,
                        ctx.author.id,
                    )
                else:
                    if player_total > dealer_total or dealer_total > 21:
                        await ctx.agree(
                            f"You win! Your total is **{player_total}** and the dealer's total is **{dealer_total}**. You win **${bet}**!"
                        )
                        await connection.execute(
                            "UPDATE economy SET balance = balance + $1 WHERE user_id = $2",
                            bet,
                            ctx.author.id,
                        )
                    else:
                        await ctx.deny(
                            f"You lose! Your total is **{player_total}** and the dealer's total is **{dealer_total}**. You lost **${bet}**."
                        )
                        await connection.execute(
                            "UPDATE economy SET balance = balance - $1 WHERE user_id = $2",
                            bet,
                            ctx.author.id,
                        )

            except Exception as e:
                print(f"Error in blackjack command: {e}")
                await ctx.deny("An error occurred during the blackjack game.")


async def setup(bot):
    await bot.add_cog(Economy(bot))
