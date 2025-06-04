import time
import random
import asyncio
import discord

from decimal import Decimal, InvalidOperation

from discord import Interaction, Embed, ButtonStyle, Member
from discord.ui import View, Button

from modules.styles import emojis, colors
from modules.evelinabot import Evelina
from modules.helpers import EvelinaContext
from modules.economy.functions import EconomyQuestsMeasures, EconomyMeasures

class SlotsButtons(discord.ui.View):
    def __init__(self, ctx, bet: Decimal, bot: Evelina):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.bet = bet
        self.bot = bot
        self.quests = EconomyQuestsMeasures(self.bot)
        self.economy = EconomyMeasures(self.bot)
        self.message = None
        self.emojis = {
            "🍒": 1.25,
            "🍊": 1.5,
            "🍇": 2,
            "🍓": 2.5,
            "🍉": 3,
            "🍋": 3.5,
            "🍎": 4,
            "🍏": 4.5,
        }
        self.result_message = None
        self.winnings = Decimal(0)
        self.awaiting_bet_change = False
        self.limit = random.randint(100000, 2000000)
        self.active = True
        self.using_winnings = False
        self.spin_count = 0
        asyncio.ensure_future(self.cache_game())

    async def cache_game(self):
        await self.bot.cache.set(f"slot_user_{self.ctx.author.id}", self)
        await self.bot.cache.set(f"slot_channel_{self.ctx.channel.id}", self)

    def check_user(self, interaction: discord.Interaction):
        return interaction.user.id == self.ctx.author.id

    async def fetch_balance(self):
        query = "SELECT cash FROM economy WHERE user_id = $1"
        record = await self.bot.db.fetchrow(query, self.ctx.author.id)
        if record:
            return Decimal(record["cash"])
        else:
            return Decimal(0)

    def create_embed(self, slots, new_bet=None, footer_text=None):
        embed = discord.Embed(description="### 🎰 Slot Machine", color=colors.NEUTRAL)
        embed.add_field(name="\u200b", value="\u200b", inline=True,)
        if len(slots) >= 3:
            embed.add_field(name=f"{self.ctx.author}'s Slots", value=f"```{slots[0]} | {slots[1]} | {slots[2]}```", inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        if self.result_message:
            embed.add_field(name="\u200b", value=f">>> {self.result_message}", inline=False)
        if self.using_winnings:
            winnings_text = f"{emojis.WARNING} **Winnings:** {self.winnings:,.2f} 💵"
        else:
            winnings_text = f"**Winnings:** {self.winnings:,.2f} 💵"
        embed.add_field(name="\u200b", value=(f"**Bet:** {self.bet:,.2f} 💵" if new_bet is None else f"**Bet:** {new_bet:,.2f} 💵"), inline=True)
        embed.add_field(name="\u200b", value=winnings_text, inline=True)
        if footer_text:
            embed.set_footer(text=footer_text)
        return embed

    async def spin_slots(self):
        self.spin_count += 1
        balance = await self.fetch_balance()
        total_bet = Decimal(self.bet)
        await self.economy.logging(self.ctx.author, Decimal(self.bet), "spent", "slots")
        if total_bet > balance:
            if self.winnings > 0:
                self.using_winnings = True
                remaining_bet = total_bet - balance
                remaining_bet = min(remaining_bet, self.winnings)
                self.winnings -= remaining_bet
                await self.bot.db.execute("UPDATE economy SET cash = cash - $1 WHERE user_id = $2", balance, self.ctx.author.id)
            else:
                self.result_message = "Not enough cash to spin!"
                await self.edit_message(["❌", "❌", "❌"])
                return None
        else:
            await self.bot.db.execute("UPDATE economy SET cash = cash - $1 WHERE user_id = $2", total_bet, self.ctx.author.id,)
        if total_bet >= self.limit:
            three_same_chance = 0.09
            two_same_chance = 0.15
        else:
            three_same_chance = 0.14
            two_same_chance = 0.24
        adjusted_weights = {symbol: weight / 200 for symbol, weight in self.emojis.items()}
        random_value = random.random()
        if random_value <= three_same_chance:
            final_result = [random.choice(list(self.emojis.keys()))] * 3
        elif random_value <= three_same_chance + two_same_chance:
            symbol = random.choice(list(self.emojis.keys()))
            other_symbol = random.choice([s for s in self.emojis.keys() if s != symbol])
            final_result = [symbol, symbol, other_symbol]
            random.shuffle(final_result)
        else:
            final_result = random.sample(list(self.emojis.keys()), 3)
        for i in range(2):
            temp_result = [random.choices(list(adjusted_weights.keys()), weights=adjusted_weights.values())[0] for _ in range(3)]
            footer_text = f"Spins: {self.spin_count} • evelina.bot"
            await self.edit_message(temp_result, footer_text=footer_text)
            await asyncio.sleep(1)
        symbol_counts = {symbol: final_result.count(symbol) for symbol in set(final_result)}
        max_count = max(symbol_counts.values())
        max_symbol = max(symbol_counts, key=symbol_counts.get)
        if max_count == 3:
            winnings_multiplier = self.emojis[max_symbol]
            win_amount = total_bet * Decimal(winnings_multiplier)
            self.result_message = f"Congratulations! You **won** {win_amount:,.2f} 💵!"
            self.winnings += win_amount
            await self.economy.logging(self.ctx.author, win_amount, "won", "slots")
        elif max_count == 2:
            winnings_multiplier = (self.emojis[max_symbol] / 2)
            win_amount = total_bet * (1 + Decimal(winnings_multiplier))
            self.result_message = f"You got **two** {max_symbol}! You **won** {win_amount:,.2f} 💵!"
            self.winnings += win_amount
            await self.economy.logging(self.ctx.author, win_amount, "won", "slots")
        else:
            self.result_message = "You **lost**. Better luck next time!"
            await self.economy.logging(self.ctx.author, total_bet, "lost", "slots")
        await self.edit_message(final_result, footer_text=footer_text)
        return final_result
    
    async def edit_message(self, slots, footer_text=None):
        await self.message.edit(embed=self.create_embed(slots, footer_text=footer_text))

    async def update_balance(self, amount):
        await self.bot.db.execute("UPDATE economy SET cash = cash + $1 WHERE user_id = $2", Decimal(amount), self.ctx.author.id)

    @discord.ui.button(label="Spin", style=discord.ButtonStyle.primary)
    async def spin_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.check_user(interaction):
            return await interaction.response.send_message("This is not your game!", ephemeral=True)
        await interaction.response.defer()
        if self.result_message:
            self.result_message = None
        for child in self.children:
            child.disabled = True
        await self.message.edit(view=self)
        slots = await self.spin_slots()
        if not slots:
            for child in self.children:
                child.disabled = False
            return await self.message.edit(view=self)
        for child in self.children:
            child.disabled = False
        await self.message.edit(embed=self.create_embed(slots), view=self)

    @discord.ui.button(label="Change Bet", style=discord.ButtonStyle.primary)
    async def change_bet_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.check_user(interaction):
            return await interaction.warn("This is not your game!", ephemeral=True)
        if self.awaiting_bet_change:
            return await interaction.warn("Please enter the new bet amount in the chat.", ephemeral=True)
        await interaction.response.defer()
        self.awaiting_bet_change = True
        for child in self.children:
            if child.label == "Change Bet":
                child.disabled = True
        await self.message.edit(view=self)
        await interaction.warn("Please enter the new bet amount in the chat.", ephemeral=True)
        def check(msg):
            return msg.author == self.ctx.author and msg.channel == self.ctx.channel
        try:
            msg = await self.bot.wait_for("message", check=check, timeout=60)
            new_bet = msg.content
            try:
                new_bet_decimal = Decimal(new_bet)
            except InvalidOperation:
                try:
                    await msg.add_reaction("❌")
                except Exception:
                    pass
                return await interaction.warn("Invalid bet amount. Please enter a valid number.", ephemeral=True)
            balance = await self.fetch_balance()
            if new_bet_decimal > 0 and new_bet_decimal <= balance:
                self.bet = new_bet_decimal
                try:
                    await msg.add_reaction("✅")
                except Exception:
                    pass
                await interaction.approve(f"Bet changed to {new_bet_decimal:,.2f} 💵", ephemeral=True)
                await self.message.edit(embed=self.create_embed(["🟦", "🟦", "🟦"], new_bet=new_bet_decimal), view=self)
                await msg.delete()
            else:
                try:
                    await msg.add_reaction("❌")
                except Exception:
                    pass
                await interaction.warn("Invalid bet amount. Please try again.", ephemeral=True)
        except asyncio.TimeoutError:
            await interaction.warn("Bet change timed out.", ephemeral=True)
        finally:
            self.awaiting_bet_change = False
            for child in self.children:
                if child.label == "Change Bet":
                    child.disabled = False
            await self.message.edit(view=self)

    @discord.ui.button(label="Exit", style=discord.ButtonStyle.danger)
    async def exit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.check_user(interaction):
            return
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=None)
        if self.winnings > 0:
            await self.bot.db.execute("UPDATE economy SET cash = cash + $1 WHERE user_id = $2", self.winnings, self.ctx.author.id)
        await self.quests.add_win_game(interaction.user, "slots")
        await self.quests.add_win_money(interaction.user, "slots", Decimal(self.winnings) - Decimal(self.bet))
        self.winnings = Decimal(0)
        self.using_winnings = False
        await self.bot.cache.remove(f"slot_user_{self.ctx.author.id}")
        await self.bot.cache.remove(f"slot_channel_{self.ctx.channel.id}")

    async def on_timeout(self):
        for button in self.children:
            button.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                pass
        if self.winnings > 0:
            await self.bot.db.execute("UPDATE economy SET cash = cash + $1 WHERE user_id = $2", self.winnings, self.ctx.author.id)
        self.winnings = Decimal(0)
        self.using_winnings = False
        await self.bot.cache.remove(f"slot_user_{self.ctx.author.id}")
        await self.bot.cache.remove(f"slot_channel_{self.ctx.channel.id}")

class LadderButtons(discord.ui.View):
    def __init__(self, ctx, amount: Decimal, bot: Evelina):
        super().__init__()
        self.ctx = ctx
        self.bet = amount
        self.bot = bot
        self.quests = EconomyQuestsMeasures(self.bot)
        self.economy = EconomyMeasures(self.bot)
        self.index = 0
        self.started = False
        self.message = None
        self.multipliers = [1, 1.25, 1.50, 1.75, 2, 2.25, 2.50, 2.75, 3]
        self.limit = 25000000
        self.emoji = "🏦"
        self.cash = "💵"
        self.card = "💳"
        self.action_in_progress = False
        self.last_interaction = {}
        self.fall_count = 0

    async def interaction_check(self, interaction: Interaction):
        if interaction.user.id != self.ctx.author.id:
            await interaction.warn("You are not the **author** of this embed", ephemeral=True)
            return False
        return True

    def create_embed(self):
        multiplier_info = '\n'.join(
            f'> {f"{emojis.IDLE}" if len(self.multipliers) - 1 - i <= self.index else f"{emojis.OFFLINE}"} {multiplier}x'
            for i, multiplier in enumerate(reversed(self.multipliers))
        )
        embed = discord.Embed(
            title=f'Playing Ladder with {self.bet:,.2f} {self.cash}',
            color=colors.ECONOMY,
            description="You will lose your bet if you fall 5 times!"
        )
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        embed.add_field(name="Multipliers", value=multiplier_info, inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        return embed

    @discord.ui.button(label='Hit', style=discord.ButtonStyle.primary)
    async def hit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.interaction_check(interaction):
            return
        await interaction.response.defer()
        user_id = interaction.user.id
        now = time.time()
        last_time = self.last_interaction.get(user_id, 0)
        if now - last_time < 2:
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are too fast, please wait a little bit...")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        self.last_interaction[user_id] = now
        def calculate_chance(bet):
            base_chance = 0.7
            decrease_rate = 0.01
            chance = base_chance - (bet / self.limit) * decrease_rate
            return max(chance, 0.1)
        chance = calculate_chance(self.bet)
        if random.random() < chance:
            self.index = min(self.index + 1, len(self.multipliers) - 1)
            self.started = True
            if self.index == len(self.multipliers) - 1:
                for child in self.children:
                    child.disabled = True
                self.collect_button.disabled = False
        else:
            self.index = max(self.index - 1, 0)
            self.started = True
            self.fall_count += 1
            if self.fall_count >= 5:
                for child in self.children:
                    child.disabled = True
                embed = discord.Embed(description=f"{emojis.LOSE} {interaction.user.mention}: You've lost **{self.bet:,.2f}** {self.cash} after falling 5 times!", color=colors.ERROR)
                for child in self.children:
                    child.disabled = True
                await self.economy.logging(interaction.user, self.bet, "lost", "ladder")
                await interaction.followup.send(embed=embed)
                return self.stop()
            if self.index == 0:
                for child in self.children:
                    child.disabled = True
                embed = discord.Embed(description=f"{emojis.LOSE} {interaction.user.mention}: You've lost **{self.bet:,.2f}** {self.cash} due to a fall.", color=colors.ERROR)
                await self.economy.logging(interaction.user, self.bet, "lost", "ladder")
                await interaction.followup.send(embed=embed)
        await interaction.followup.edit_message(message_id=interaction.message.id, embed=self.create_embed(), view=self)

    @discord.ui.button(label='Collect', style=discord.ButtonStyle.primary, custom_id='collect_button')
    async def collect_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.interaction_check(interaction):
            return
        await interaction.response.defer()
        user_id = interaction.user.id
        now = time.time()
        last_time = self.last_interaction.get(user_id, 0)
        if now - last_time < 2:
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are too fast, please wait a little bit...")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        self.last_interaction[user_id] = now
        winnings = Decimal(self.bet) * Decimal(self.multipliers[self.index])
        self.index = 0
        for child in self.children:
            child.disabled = True
        await self.quests.add_win_game(interaction.user, "ladder")
        await self.quests.add_win_money(interaction.user, "ladder", Decimal(winnings) - Decimal(self.bet))
        self.bet = Decimal('0')
        await self.bot.db.execute("UPDATE economy SET cash = cash + $1 WHERE user_id = $2", winnings, interaction.user.id)
        await interaction.approve(f"You've successfully collected **{winnings:,.2f}** {self.cash}")
        await self.economy.logging(interaction.user, winnings, "won", "ladder")
        await interaction.followup.edit_message(message_id=interaction.message.id, view=self)
        self.stop()

    @discord.ui.button(label='Exit', style=discord.ButtonStyle.danger)
    async def exit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.interaction_check(interaction):
            return
        await interaction.response.defer()
        user_id = interaction.user.id
        now = time.time()
        last_time = self.last_interaction.get(user_id, 0)
        if now - last_time < 2:
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are too fast, please wait a little bit...")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        self.last_interaction[user_id] = now
        for child in self.children:
            child.disabled = True
        await self.bot.db.execute("UPDATE economy SET cash = cash + $1 WHERE user_id = $2", self.bet, interaction.user.id)
        await interaction.approve(f"Your bet of **{self.bet:,.2f}** {self.cash} has been returned.")
        await self.economy.logging(interaction.user, self.bet, "returned", "ladder")
        await interaction.followup.edit_message(message_id=interaction.message.id, view=self)
        self.stop()

    def stop(self):
        super().stop()

class BlackjackButtons(discord.ui.View):
    def __init__(self, ctx, amount: Decimal, bot: Evelina):
        super().__init__()
        self.ctx = ctx
        self.bet = amount
        self.bot = bot
        self.quests = EconomyQuestsMeasures(self.bot)
        self.economy = EconomyMeasures(self.bot)
        self.message = None
        self.deck = self.generate_deck()
        self.player_hand = []
        self.dealer_hand = []
        self.player_score = 0
        self.dealer_score = 0
        self.started = False
        self.stand = False
        self.double_down_used = False
        self.game_active = True
        self.initial_deal()
        self.emoji = "🏦"
        self.cash = "💵"
        self.card = "💳"
        self.first_hit = False
        self.last_interaction = {}

    def check_user(self, interaction: discord.Interaction):
        return interaction.user.id == self.ctx.author.id

    def generate_deck(self):
        suits = ['♠', '♣', '♥', '♦']
        values = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        emojis_array = {
            '♣': {'2': emojis.CLUBS_2, '3': emojis.CLUBS_3, '4': emojis.CLUBS_4, '5': emojis.CLUBS_5, '6': emojis.CLUBS_6, '7': emojis.CLUBS_7,
                  '8': emojis.CLUBS_8, '9': emojis.CLUBS_9, '10': emojis.CLUBS_10, 'J': emojis.CLUBS_J, 'Q': emojis.CLUBS_Q, 'K': emojis.CLUBS_K, 'A': emojis.CLUBS_A},
            '♥': {'2': emojis.HEART_2, '3': emojis.HEART_3, '4': emojis.HEART_4, '5': emojis.HEART_5, '6': emojis.HEART_6, '7': emojis.HEART_7,
                  '8': emojis.HEART_8, '9': emojis.HEART_9, '10': emojis.HEART_10, 'J': emojis.HEART_J, 'Q': emojis.HEART_Q, 'K': emojis.HEART_K, 'A': emojis.HEART_A},
            '♠': {'2': emojis.SPADE_2, '3': emojis.SPADE_3, '4': emojis.SPADE_4, '5': emojis.SPADE_5, '6': emojis.SPADE_6, '7': emojis.SPADE_7,
                  '8': emojis.SPADE_8, '9': emojis.SPADE_9, '10': emojis.SPADE_10, 'J': emojis.SPADE_J, 'Q': emojis.SPADE_Q, 'K': emojis.SPADE_K, 'A': emojis.SPADE_A},
            '♦': {'2': emojis.DIAMOND_2, '3': emojis.DIAMOND_3, '4': emojis.DIAMOND_4, '5': emojis.DIAMOND_5, '6': emojis.DIAMOND_6, '7': emojis.DIAMOND_7,
                  '8': emojis.DIAMOND_8, '9': emojis.DIAMOND_9, '10': emojis.DIAMOND_10, 'J': emojis.DIAMOND_J, 'Q': emojis.DIAMOND_Q, 'K': emojis.DIAMOND_K, 'A': emojis.DIAMOND_A}
        }
        return [{'value': value, 'suit': suit, 'emoji': emojis_array[suit][value]} for value in values for suit in suits]

    def initial_deal(self):
        self.player_hand.append(self.deck.pop(random.randint(0, len(self.deck) - 1)))
        self.dealer_hand.append(self.deck.pop(random.randint(0, len(self.deck) - 1)))
        self.calculate_score()

    def deal_second_cards(self):
        self.player_hand.append(self.deck.pop(random.randint(0, len(self.deck) - 1)))
        self.dealer_hand.append(self.deck.pop(random.randint(0, len(self.deck) - 1)))
        self.calculate_score()

    def calculate_score(self):
        self.player_score = self.calculate_hand_score(self.player_hand)
        self.dealer_score = self.calculate_hand_score(self.dealer_hand)

    def calculate_hand_score(self, hand):
        score = 0
        aces = 0
        for card in hand:
            if card['value'] in ['J', 'Q', 'K']:
                score += 10
            elif card['value'] == 'A':
                aces += 1
                score += 11
            else:
                score += int(card['value'])
        while score > 21 and aces:
            score -= 10
            aces -= 1
        return score

    def create_embed(self, reveal_dealer=False, result_message=None, result_color=None):
        player_hand = ' '.join(card['emoji'] for card in self.player_hand)
        if reveal_dealer:
            dealer_hand = ' '.join(card['emoji'] for card in self.dealer_hand)
            dealer_score = self.dealer_score
        else:
            dealer_hand = f"{emojis.CARD} {self.dealer_hand[0]['emoji']}"
            dealer_score = self.get_card_value(self.dealer_hand[0])
        embed = discord.Embed(title=f'Playing Blackjack with {self.bet:,.2f} {self.cash}', color=colors.NEUTRAL)
        embed.add_field(name=f"{self.ctx.author}'s Hand ({self.player_score})", value=player_hand, inline=True)
        embed.add_field(name=f"Dealer's Hand ({dealer_score})", value=dealer_hand, inline=True)
        if result_message:
            embed.description = f"> {result_message}"
            embed.color = result_color
        return embed

    def get_card_value(self, card):
        if card['value'] in ['J', 'Q', 'K']:
            return 10
        elif card['value'] == 'A':
            return 11
        return int(card['value'])

    async def update_balance(self, amount):
        await self.bot.db.execute("UPDATE economy SET cash = cash + $1 WHERE user_id = $2", amount, self.ctx.author.id)

    async def disable_exit_button(self, interaction: discord.Interaction):
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.label == 'Exit':
                child.disabled = True
        await interaction.followup.edit_message(message_id=interaction.message.id, view=self)

    @discord.ui.button(label='Hit', style=discord.ButtonStyle.primary)
    async def hit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.check_user(interaction):
            return await interaction.warn(f"You are not the **author** of this embed", ephemeral=True)
        
        await interaction.response.defer()

        user_id = interaction.user.id
        now = time.time()
        last_time = self.last_interaction.get(user_id, 0)
        if now - last_time < 2:
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are too fast, please wait a little bit...")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        self.last_interaction[user_id] = now

        await self.disable_exit_button(interaction)
        if not self.started:
            check = await self.bot.db.fetchrow("SELECT cash FROM economy WHERE user_id = $1", interaction.user.id)
            if self.bet > check["cash"]:
                return await interaction.error(f"You don't have enough balance to play this game!", ephemeral=True)
            self.started = True
            check = await self.bot.db.fetchrow("SELECT cash FROM economy WHERE user_id = $1", interaction.user.id)
            if self.bet > check["cash"]:
                return await interaction.error(f"You don't have enough balance to play this game!", ephemeral=True)
            await self.bot.db.execute("UPDATE economy SET cash = cash - $1 WHERE user_id = $2", self.bet, interaction.user.id)
        if len(self.player_hand) == 1:
            self.deal_second_cards()
        else:
            self.player_hand.append(self.deck.pop(random.randint(0, len(self.deck) - 1)))
            self.calculate_score()
        
        if not self.first_hit:
            self.first_hit = True
            for child in self.children:
                if isinstance(child, discord.ui.Button) and (child.label == 'Stand' or child.label == 'Double Down'):
                    child.disabled = False
            await interaction.followup.edit_message(message_id=interaction.message.id, view=self)

        if self.player_score > 21:
            result_message = f"You've busted and lost **{self.bet:,.2f}** {self.cash}"
            result_color = colors.ERROR
            await self.economy.logging(interaction.user, self.bet, "lost", "blackjack")
            await interaction.followup.edit_message(message_id=interaction.message.id, embed=self.create_embed(reveal_dealer=True, result_message=result_message, result_color=result_color), view=None)
            return self.stop()
        await interaction.followup.edit_message(message_id=interaction.message.id, embed=self.create_embed())

    @discord.ui.button(label='Stand', style=discord.ButtonStyle.green, disabled=True)
    async def stand_button(self, interaction: discord.Interaction, button: discord.ui.Button, from_double_down=False):
        if not self.check_user(interaction):
            return await interaction.warn(f"You are not the **author** of this embed", ephemeral=True)
        
        await interaction.response.defer()

        user_id = interaction.user.id
        now = time.time()
        last_time = self.last_interaction.get(user_id, 0)
        if now - last_time < 2:
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are too fast, please wait a little bit...")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        self.last_interaction[user_id] = now

        if not self.game_active:
            return await interaction.warn(f"The game has already been concluded!", ephemeral=True)
        if not from_double_down:
            await self.disable_exit_button(interaction)
        if len(self.player_hand) == 1:
            self.deal_second_cards()
        while self.dealer_score < 17:
            self.dealer_hand.append(self.deck.pop(random.randint(0, len(self.deck) - 1)))
            self.calculate_score()
        if self.dealer_score > 21 or self.player_score > self.dealer_score:
            result_message = f"Congratulations! You won **{self.bet * 2:,.2f}** {self.cash}"
            result_color = colors.SUCCESS
            await self.quests.add_win_game(interaction.user, "blackjack")
            await self.quests.add_win_money(interaction.user, "blackjack", Decimal(self.bet))
            await self.economy.logging(interaction.user, Decimal(self.bet * 2), "won", "blackjack")
            await self.update_balance(self.bet * 2)
        elif self.player_score < self.dealer_score:
            if self.double_down_used:
                loss_amount = self.bet
            else:
                loss_amount = self.bet
            result_message = f"The dealer wins. You lost **{loss_amount:,.2f}** {self.cash}"
            result_color = colors.ERROR
            await self.economy.logging(interaction.user, loss_amount, "lost", "blackjack")
        else:
            result_message = "It's a tie!"
            result_color = colors.NEUTRAL
            await self.economy.logging(interaction.user, self.bet, "tie", "blackjack")
            await self.update_balance(self.bet)
        await interaction.followup.edit_message(message_id=interaction.message.id, embed=self.create_embed(reveal_dealer=True, result_message=result_message, result_color=result_color), view=None)
        self.stop()
        self.game_active = False

    @discord.ui.button(label='Double Down', style=discord.ButtonStyle.secondary, disabled=True)
    async def double_down_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.check_user(interaction):
            return await interaction.warn(f"You are not the **author** of this embed", ephemeral=True)
        
        await interaction.response.defer()

        user_id = interaction.user.id
        now = time.time()
        last_time = self.last_interaction.get(user_id, 0)
        if now - last_time < 2:
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are too fast, please wait a little bit...")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        self.last_interaction[user_id] = now

        if self.double_down_used:
            return await interaction.warn(f"You can't double down more than one time!", ephemeral=True)
        await self.disable_exit_button(interaction)
        required_balance = self.bet
        user_balance = await self.bot.db.fetchval("SELECT cash FROM economy WHERE user_id = $1", self.ctx.author.id)
        if user_balance is None or user_balance < required_balance:
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You don't have enough balance to double down!")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        await self.bot.db.execute("UPDATE economy SET cash = cash - $1 WHERE user_id = $2", self.bet, self.ctx.author.id)
        self.bet = required_balance * 2
        self.double_down_used = True
        self.player_hand.append(self.deck.pop(random.randint(0, len(self.deck) - 1)))
        self.calculate_score()
        if self.player_score > 21:
            result_message = f"You've busted and lost **{self.bet:,.2f}** {self.cash}"
            result_color = colors.ERROR
            await self.economy.logging(interaction.user, self.bet, "lost", "blackjack")
            await interaction.followup.edit_message(message_id=interaction.message.id, embed=self.create_embed(reveal_dealer=True, result_message=result_message, result_color=result_color), view=None)
            return self.stop()
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.label == 'Double Down':
                child.disabled = True
        await interaction.followup.edit_message(message_id=interaction.message.id, embed=self.create_embed())
        self.stand = True

    @discord.ui.button(label='Exit', style=discord.ButtonStyle.danger)
    async def exit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.check_user(interaction):
            return await interaction.warn("You are not the **author** of this embed", ephemeral=True)
        
        await interaction.response.defer()

        user_id = interaction.user.id
        now = time.time()
        last_time = self.last_interaction.get(user_id, 0)
        if now - last_time < 2:
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are too fast, please wait a little bit...")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        self.last_interaction[user_id] = now

        for child in self.children:
            child.disabled = True
        await interaction.followup.edit_message(message_id=interaction.message.id, view=self)
        if not self.started:
            embed = discord.Embed(description=f"{emojis.APPROVE} {interaction.user.mention}: Your bet of **{self.bet:,.2f}** {self.cash} has been returned.", color=colors.SUCCESS)
            await self.economy.logging(interaction.user, self.bet, "returned", "blackjack")
            await interaction.followup.send(embed=embed)
            return self.stop()
        await self.bot.db.execute("UPDATE economy SET cash = cash + $1 WHERE user_id = $2", self.bet, self.ctx.author.id)
        embed = discord.Embed(description=f"{emojis.APPROVE} {interaction.user.mention}: Your bet of **{self.bet:,.2f}** {self.cash} has been returned.", color=colors.SUCCESS)
        await self.economy.logging(interaction.user, self.bet, "returned", "blackjack")
        await interaction.followup.send(embed=embed)
        return self.stop()

class MinesButtons(discord.ui.View):
    def __init__(self, ctx, amount: Decimal, bot: Evelina, mines, count, multipliers):
        super().__init__()
        self.ctx = ctx
        self.bet = amount
        self.bot = bot
        self.quests = EconomyQuestsMeasures(self.bot)
        self.economy = EconomyMeasures(self.bot)
        self.grid_size = 4
        self.count = count
        self.correct_guesses = 0
        self.mines = mines
        self.revealed = [[False] * self.grid_size for _ in range(self.grid_size)]
        self.multipliers = multipliers
        self.message = None
        self.action_in_progress = False
        self.create_buttons()
        self.emoji = "🏦"
        self.cash = "💵"
        self.card = "💳"

    @staticmethod
    def generate_mines_static(grid_size=4, count=4):
        mines = set()
        while len(mines) < count:
            x = random.randint(0, grid_size - 1)
            y = random.randint(0, grid_size - 1)
            mines.add((x, y))
        return mines

    def generate_mines(self):
        return self.mines

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            if interaction.user.id == 335500798752456705:
                mines_display = [["⬜" for _ in range(self.grid_size)] for _ in range(self.grid_size)]
                for x, y in self.mines:
                    mines_display[x][y] = "💣"
                mines_str = "\n".join(" ".join(row) for row in mines_display)
                await interaction.response.send_message(f"\n{mines_str}", ephemeral=True)
            else:
                await interaction.warn("You are not the **author** of this embed", ephemeral=True)
            return False
        return True

    def create_buttons(self):
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                button = discord.ui.Button(label='‎', style=discord.ButtonStyle.secondary, custom_id=f"{i}-{j}", row=i)
                button.callback = self.create_reveal_callback(i, j)
                self.add_item(button)

        collect_button = discord.ui.Button(label='Collect', style=discord.ButtonStyle.primary)
        collect_button.callback = self.collect_button_callback
        self.add_item(collect_button)

        exit_button = discord.ui.Button(label='Exit', style=discord.ButtonStyle.danger)
        exit_button.callback = self.exit_button_callback
        self.add_item(exit_button)

    def create_reveal_callback(self, x, y):
        async def reveal(interaction: discord.Interaction):
            if not await self.interaction_check(interaction) or getattr(self, 'action_in_progress', False):
                return
            await interaction.response.defer()
            self.action_in_progress = True
            if self.revealed[x][y]:
                await interaction.warn("This tile is already revealed!", ephemeral=True)
                self.action_in_progress = False
                return
            self.revealed[x][y] = True
            if (x, y) in self.mines:
                await self.handle_loss(interaction)
            else:
                self.correct_guesses += 1
                button = next(filter(lambda b: b.custom_id == f"{x}-{y}", self.children), None)
                if button:
                    button.label = '‎'
                    button.style = discord.ButtonStyle.success
                    await interaction.followup.edit_message(message_id=interaction.message.id, view=self)
                await self.update_embed(interaction)
                if self.correct_guesses + self.count == self.grid_size ** 2:
                    await self.handle_auto_collect(interaction)
            self.action_in_progress = False
        return reveal

    def calculate_multiplier(self):
        if self.correct_guesses == 0:
            return Decimal(1)
        start_index = self.count - 1
        multiplier_index = start_index + self.correct_guesses - 1
        return Decimal(self.multipliers[multiplier_index])

    def calculate_winnings(self):
        if self.correct_guesses == 0:
            return Decimal(0)
        multiplier = self.calculate_multiplier()
        winnings = Decimal(self.bet) * multiplier
        return winnings

    async def handle_auto_collect(self, interaction: discord.Interaction):
        winnings = self.calculate_winnings()
        for index, child in enumerate(self.children):
            if isinstance(child, discord.ui.Button):
                child.disabled = True
                if '-' in child.custom_id:
                    coords = tuple(map(int, child.custom_id.split('-')))
                    if coords in self.mines:
                        child.label = '💣'
                        child.style = discord.ButtonStyle.danger
                    elif self.revealed[coords[0]][coords[1]]:
                        child.style = discord.ButtonStyle.success
                    else:
                        child.style = discord.ButtonStyle.secondary
        await self.bot.db.execute("UPDATE economy SET cash = cash + $1 WHERE user_id = $2", winnings, interaction.user.id)
        await interaction.followup.edit_message(message_id=interaction.message.id, view=self)
        auto_win_embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Congratulations, you've cleared the board and won **{winnings:,.2f}** {self.cash}")
        await self.quests.add_win_game(interaction.user, "mines")
        await self.quests.add_win_money(interaction.user, "mines", Decimal(winnings) - Decimal(self.bet))
        await self.economy.logging(interaction.user, Decimal(winnings) - Decimal(self.bet), "won", "mines")
        await interaction.followup.send(embed=auto_win_embed)

    async def collect_button_callback(self, interaction: discord.Interaction):
        if not await self.interaction_check(interaction) or getattr(self, 'action_in_progress', False):
            return
        await interaction.response.defer()
        self.action_in_progress = True
        winnings = self.calculate_winnings()
        if winnings < 10:
            await interaction.warn(f"You can't collect **{winnings:,.2f}** {self.cash}", ephemeral=True)
            self.action_in_progress = False
            return
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
                if '-' in child.custom_id:
                    coords = tuple(map(int, child.custom_id.split('-')))
                    if coords in self.mines:
                        child.label = '💣'
                        child.style = discord.ButtonStyle.danger
                    elif self.revealed[coords[0]][coords[1]]:
                        child.style = discord.ButtonStyle.success
                    else:
                        child.style = discord.ButtonStyle.secondary
        await self.bot.db.execute("UPDATE economy SET cash = cash + $1 WHERE user_id = $2", winnings, interaction.user.id)
        await interaction.approve(f"You've successfully collected **{winnings:,.2f}** {self.cash}")
        await self.quests.add_win_game(interaction.user, "mines")
        await self.quests.add_win_money(interaction.user, "mines", Decimal(winnings) - Decimal(self.bet))
        await self.economy.logging(interaction.user, Decimal(winnings) - Decimal(self.bet), "won", "mines")
        await interaction.followup.edit_message(message_id=interaction.message.id, view=self)
        self.action_in_progress = False

    async def exit_button_callback(self, interaction: discord.Interaction):
        if not await self.interaction_check(interaction):
            return
        await interaction.response.defer()
        self.action_in_progress = True
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
                if '-' in child.custom_id:
                    coords = tuple(map(int, child.custom_id.split('-')))
                    if coords in self.mines:
                        child.label = '💣'
                        child.style = discord.ButtonStyle.danger
                    else:
                        child.label = '‎'
                        child.style = discord.ButtonStyle.secondary
        await self.bot.db.execute("UPDATE economy SET cash = cash + $1 WHERE user_id = $2", self.bet, interaction.user.id)
        await interaction.approve(f"Your bet of **{self.bet:,.2f}** {self.cash} has been returned.")
        await self.economy.logging(interaction.user, self.bet, "returned", "mines")
        await interaction.followup.edit_message(message_id=interaction.message.id, view=self)
        self.action_in_progress = False
        self.stop()

    def create_embed(self):
        multiplier = self.calculate_multiplier()
        winnings = self.calculate_winnings()
        embed = discord.Embed(title=f'Playing Mines with {self.bet:,.2f} {self.cash} and {self.count} mines', color=colors.ECONOMY)
        embed.add_field(name="Fields", value=f"{self.correct_guesses} / {self.grid_size ** 2 - self.count}", inline=True)
        embed.add_field(name="Multiplier", value=f"{multiplier:,.2f}", inline=True)
        embed.add_field(name="Winnings", value=f"{winnings:,.2f} {self.cash}", inline=True)
        return embed

    async def update_embed(self, interaction: discord.Interaction):
        embed = self.create_embed()
        await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=self)

    async def handle_loss(self, interaction: discord.Interaction):
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
                if '-' in child.custom_id:
                    coords = tuple(map(int, child.custom_id.split('-')))
                    if coords in self.mines:
                        child.label = '💣'
                        child.style = discord.ButtonStyle.danger
                    elif self.revealed[coords[0]][coords[1]]:
                        child.style = discord.ButtonStyle.success
                    else:
                        child.style = discord.ButtonStyle.secondary
        await interaction.error(f"You hit a mine! You lost **{self.bet:,.2f}** {self.cash}")
        await self.economy.logging(interaction.user, self.bet, "lost", "mines")
        await interaction.followup.edit_message(message_id=interaction.message.id, view=self)

    async def handle_win(self, interaction: discord.Interaction):
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        winnings = self.calculate_winnings()
        await self.bot.db.execute("UPDATE economy SET cash = cash + $1 WHERE user_id = $2", winnings, interaction.user.id)
        await interaction.followup.edit_message(message_id=interaction.message.id, view=self)
        await self.economy.logging(interaction.user, Decimal(winnings) - Decimal(self.bet), "won", "mines")
        await interaction.followup.send(f"Congratulations, you've cleared the board and won **{winnings:,.2f}** {self.cash}")

class RandomButtonView(discord.ui.View):
    def __init__(self, ctx, amounts, bot):
        super().__init__()
        self.ctx = ctx
        self.amounts = amounts
        self.bot = bot
        self.quests = EconomyQuestsMeasures(self.bot)
        self.economy = EconomyMeasures(self.bot)
        self.revealed = False
        self.create_buttons()
        self.emoji = "🏦"
        self.cash = "💵"
        self.card = "💳"

    def create_buttons(self):
        for i in range(3):
            button = discord.ui.Button(label='‎', style=discord.ButtonStyle.primary, custom_id=str(i))
            button.callback = self.create_reveal_callback(i)
            self.add_item(button)

    def create_reveal_callback(self, index):
        async def reveal(interaction: discord.Interaction):
            if interaction.user.id != self.ctx.author.id or self.revealed:
                return

            self.revealed = True

            for i, button in enumerate(self.children):
                if isinstance(button, discord.ui.Button):
                    button.disabled = True
                    if i == index:
                        button.style = discord.ButtonStyle.success
                        check = await self.bot.db.fetchrow("SELECT * FROM economy WHERE user_id = $1", interaction.user.id)
                        cash = check["cash"]
                        await self.bot.db.execute("UPDATE economy SET cash = cash + $1 WHERE user_id = $2", self.amounts[i], interaction.user.id)
                        await self.quests.add_collect_money(interaction.user, "bonus", Decimal(self.amounts[i]))
                        await self.economy.logging(interaction.user, Decimal(self.amounts[i]), "collected", "bonus")
                        await interaction.approve(f"Congratulations! You won **{self.amounts[i]:,.2f}** {self.cash}")
                    button.label = f"{self.amounts[i]:,.2f}"

            await interaction.message.edit(view=self)

        return reveal

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id == self.ctx.author.id
    
class BusinessTransferView(View):
    def __init__(self, ctx: EvelinaContext, bot: Evelina, member: discord.Member, business, price: int):
        super().__init__()
        self.ctx = ctx
        self.bot = bot
        self.economy = EconomyMeasures(self.bot)
        self.member = member
        self.business = business
        self.price = price
        self.status = False
        self.emoji = "🏦"
        self.cash = "💵"
        self.card = "💳"

    async def interaction_check(self, interaction: Interaction):
        if interaction.user == self.ctx.author:
            await interaction.warn("You can't interact with your own business transfer.", ephemeral=True)
            return False
        elif interaction.user != self.member:
            await interaction.warn("You are not the recipient of this business transfer.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Approve", style=ButtonStyle.success)
    async def yes(self, interaction: Interaction, button: Button):
        user_business = await self.ctx.bot.db.fetchrow("SELECT * FROM business WHERE owner = $1", self.member.id)
        if user_business:
            await interaction.error(f"You already own a business.", ephemeral=True)
            return
        user_balance = await self.ctx.bot.db.fetchval("SELECT cash FROM economy WHERE user_id = $1", self.member.id)
        if user_balance < self.price:
            await interaction.error(f"You don't have enough money to buy this business.", ephemeral=True)
            return
        await self.ctx.bot.db.execute("UPDATE business SET owner = $1 WHERE id = $2", self.member.id, self.business["id"])
        await self.ctx.bot.db.execute("UPDATE economy SET cash = cash - $1 WHERE user_id = $2", self.price, self.member.id)
        await self.ctx.bot.db.execute("UPDATE economy SET cash = cash + $1 WHERE user_id = $2", self.price, self.ctx.author.id)
        check = await self.bot.db.fetchrow("SELECT * FROM economy_cards_used WHERE user_id = $1 AND business = $2", self.ctx.author.id, "business")
        if check:
            await self.ctx.bot.db.execute("UPDATE economy_cards_user SET active = True WHERE user_id = $1 AND card_id = $2", self.ctx.author.id, check['card_id'])
            await self.ctx.bot.db.execute("DELETE FROM economy_cards_used WHERE user_id = $1 AND card_id = $2", self.ctx.author.id, check)
        await self.economy.logging(self.ctx.author, Decimal(self.price), "transferred", "business")
        await self.economy.logging(self.member, Decimal(self.price), "received", "business")
        await interaction.response.edit_message(content=None, embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {self.ctx.author.mention}: Successfully transferred the business **{self.business['name']}** to {self.member.mention} for **{self.bot.misc.humanize_number(self.price)}** {self.cash}"), view=None)
        self.status = True

    @discord.ui.button(label="Decline", style=ButtonStyle.danger)
    async def no(self, interaction: Interaction, button: Button):
        await interaction.response.edit_message(content=f"{self.ctx.author.mention}", embed=Embed(color=colors.ERROR, description=f"{emojis.DENY} {self.member.mention}: Declined the business transfer."), view=None)
        self.status = True

class BusinessExchangeView(View):
    def __init__(self, ctx: EvelinaContext, bot: Evelina, member: discord.Member, user_business, target_business, price: int):
        super().__init__()
        self.ctx = ctx
        self.bot = bot
        self.economy = EconomyMeasures(self.bot)
        self.member = member
        self.user_business = user_business
        self.target_business = target_business
        self.price = price
        self.status = False
        self.emoji = "🏦"
        self.cash = "💵"
        self.card = "💳"

    async def interaction_check(self, interaction: Interaction):
        if interaction.user == self.ctx.author:
            await interaction.warn("You can't interact with your own business exchange.", ephemeral=True)
            return False
        elif interaction.user != self.member:
            await interaction.warn("You are not the recipient of this business exchange.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Approve", style=ButtonStyle.success)
    async def yes(self, interaction: Interaction, button: Button):
        user_balance = await self.ctx.bot.db.fetchval("SELECT cash FROM economy WHERE user_id = $1", self.member.id)
        if user_balance < self.price:
            await interaction.error(f"You don't have enough money to pay the additional price.", ephemeral=True)
            return
        await self.ctx.bot.db.execute("UPDATE business SET owner = $1 WHERE id = $2", self.member.id, self.user_business["id"])
        await self.ctx.bot.db.execute("UPDATE business SET owner = $1 WHERE id = $2", self.ctx.author.id, self.target_business["id"])
        await self.ctx.bot.db.execute("UPDATE economy SET cash = cash - $1 WHERE user_id = $2", self.price, self.member.id)
        await self.ctx.bot.db.execute("UPDATE economy SET cash = cash + $1 WHERE user_id = $2", self.price, self.ctx.author.id)
        await self.economy.logging(self.ctx.author, Decimal(self.price), "exchanged", "business")
        await self.economy.logging(self.member, Decimal(self.price), "exchanged", "business")
        await interaction.response.edit_message(content=None, embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {self.ctx.author.mention} and {self.member.mention} have successfully exchanged their businesses.\n"
                                                                                           f"**{self.ctx.author.mention} Business:** {self.user_business['name']} #{self.user_business['id']}\n"
                                                                                           f"**{self.member.mention} Business:** {self.target_business['name']} #{self.target_business['id']}\n"
                                                                                           f"**Additional Price:** {self.bot.misc.humanize_number(self.price)} {self.cash}"), view=None)
        self.status = True

    @discord.ui.button(label="Decline", style=ButtonStyle.danger)
    async def no(self, interaction: Interaction, button: Button):
        await interaction.response.edit_message(content=f"{self.ctx.author.mention}", embed=Embed(color=colors.ERROR, description=f"{emojis.DENY} {self.member.mention}: Declined the business exchange."), view=None)
        self.status = True

class ConfirmView(View):
    def __init__(self, ctx, bot, card_id, amount, price, yes_callback, no_callback, target_user):
        super().__init__()
        self.ctx = ctx
        self.bot = bot
        self.card_id = card_id
        self.amount = amount
        self.price = price
        self.yes_callback = yes_callback
        self.no_callback = no_callback
        self.target_user = target_user
        self.message = None

    def set_message(self, message):
        self.message = message

    async def interaction_check(self, interaction: Interaction):
        if interaction.user != self.target_user:
            await interaction.response.send_message(f"You are not authorized to respond to this exchange, only {self.target_user.mention} can.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Yes", style=ButtonStyle.success)
    async def yes(self, interaction: Interaction, button: Button):
        await self.yes_callback(interaction)

    @discord.ui.button(label="No", style=ButtonStyle.danger)
    async def no(self, interaction: Interaction, button: Button):
        await self.no_callback(interaction)

class CrashView(View):
    def __init__(self, ctx, amount: Decimal, bot: Evelina):
        super().__init__()
        self.ctx = ctx
        self.amount = amount
        self.bot = bot
        self.quests = EconomyQuestsMeasures(self.bot)
        self.economy = EconomyMeasures(self.bot)
        self.cash = "💵"
        self.multiplier = 1.0
        self.crashed = False
        self.message = None
        self.cashout_done = False
        self.final_multiplier = None

    @discord.ui.button(label="Cashout", style=ButtonStyle.primary, custom_id="cashout")
    async def cashout(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.ctx.author.id != interaction.user.id:
            return await interaction.warn("You are not the **author** of this embed", ephemeral=True)
        if self.cashout_done or self.crashed:
            return
        self.cashout_done = True
        cashout_multiplier = self.multiplier
        winnings = self.amount * cashout_multiplier
        while not self.crashed:
            if random.random() >= 0.85:
                self.crashed = True
            else:
                self.multiplier += random.uniform(0.12, 0.25)
        self.final_multiplier = self.multiplier
        self.stop()
        embed = Embed(
            title=f"Player Crash with {self.amount:,.2f} {self.cash}",
            description=f"> Congratulations! You won **{winnings:,.2f}** {self.cash}",
            color=colors.SUCCESS
        )
        embed.add_field(name="Multiplier", value=f"{cashout_multiplier:,.2f}x", inline=True)
        embed.add_field(name="Crash", value=f"{self.final_multiplier:,.2f}x", inline=True)
        embed.add_field(name="Winnings", value=f"{winnings:,.2f} {self.cash}", inline=True)
        await interaction.response.edit_message(embed=embed, view=None)
        await self.quests.add_win_game(interaction.user, "crash")
        await self.quests.add_win_money(interaction.user, "crash", Decimal(winnings) - Decimal(self.amount))
        await self.economy.logging(interaction.user, Decimal(winnings) - Decimal(self.amount), "won", "crash")
        await self.bot.db.execute("UPDATE economy SET cash = cash + $1 WHERE user_id = $2", winnings, interaction.user.id)

    async def start_crash(self):
        while not self.crashed and not self.cashout_done:
            await asyncio.sleep(2.5)
            if self.cashout_done:
                break
            if random.random() >= 0.85:
                self.crashed = True
                self.final_multiplier = self.multiplier
                embed = Embed(
                    title=f"Player Crash with {self.amount:,.2f} {self.cash}",
                    description=f"> Crashed! You lost **{self.amount:,.2f}** {self.cash}",
                    color=colors.ERROR
                )
                embed.add_field(name="Multiplier", value=f"{self.multiplier:,.2f}x", inline=True)
                embed.add_field(name="Crash", value=f"{self.final_multiplier:,.2f}x", inline=True)
                embed.add_field(name="Losses", value=f"{self.amount:,.2f} {self.cash}", inline=True)
                await self.economy.logging(self.ctx.author, self.amount, "lost", "crash")
                await self.message.edit(embed=embed, view=None)
                self.stop()
            else:
                self.multiplier += random.uniform(0.07, 0.20)
                winnings = self.amount * self.multiplier
                embed = Embed(
                    title=f"Player Crash with {self.amount:,.2f} {self.cash}",
                    description=f"> Click **Cashout** button to cashout",
                    color=colors.NEUTRAL
                )
                embed.add_field(name="Multiplier", value=f"{self.multiplier:,.2f}x", inline=True)
                embed.add_field(name="Winnings", value=f"{winnings:,.2f} {self.cash}", inline=True)
                await self.message.edit(embed=embed)

class HigherLowerView(View):
    def __init__(self, ctx, amount, bot: Evelina):
        super().__init__()
        self.ctx = ctx
        self.amount = amount
        self.bot = bot
        self.quests = EconomyQuestsMeasures(self.bot)
        self.economy = EconomyMeasures(self.bot)
        self.cash = "💵"
        self.number = random.randint(2, 99)
        self.current = self.number
        self.total_multiplier = 1.00
        self.first_click = True
        self.previous_higher_multiplier = 0.0
        self.previous_lower_multiplier = 0.0
        self.update_multipliers()
        self.embed = self.create_embed()
        self.last_interaction = {}
        self.click_count = 0
        self.max_clicks = 5
        self.lock = asyncio.Lock()
    
    async def interaction_check(self, interaction: Interaction):
        if interaction.user.id != self.ctx.author.id:
            await interaction.warn("You are not the **author** of this embed", ephemeral=True)
            return False
        return True

    async def send_initial_message(self):
        self.message = await self.ctx.send(embed=self.embed, view=self)

    def update_multipliers(self):
        possible_higher = 100 - self.current
        possible_lower = self.current - 1
        if not self.first_click:
            self.previous_higher_multiplier = self.higher_multiplier
            self.previous_lower_multiplier = self.lower_multiplier
        self.higher_multiplier = ((100 / possible_higher) - 1) * 0.25 + 1 if possible_higher > 0 else 1.0
        self.lower_multiplier = ((100 / possible_lower) - 1) * 0.25 + 1 if possible_lower > 0 else 1.0
        if not self.first_click:
            if self.last_prediction == "lower":
                self.total_multiplier += self.previous_lower_multiplier - 1
            elif self.last_prediction == "higher":
                self.total_multiplier += self.previous_higher_multiplier - 1
        self.total_multiplier = max(self.total_multiplier, 1.00)

    def create_embed(self):
        embed = Embed(color=colors.NEUTRAL)
        embed.set_author(name=f"Playing Higher or Lower with {self.amount:,.2f} {self.cash}")
        embed.add_field(name="Number", value=f"{self.current}", inline=True)
        embed.add_field(name="Higher", value=f"{self.higher_multiplier:.2f}x", inline=True)
        embed.add_field(name="Lower", value=f"{self.lower_multiplier:.2f}x", inline=True)
        embed.add_field(name="Total", value=f"{self.total_multiplier:.2f}x", inline=True)
        embed.add_field(name="Winnings", value=f"{self.amount * self.total_multiplier:,.2f} {self.cash}", inline=True)
        return embed

    @discord.ui.button(label="Higher", style=ButtonStyle.green, custom_id="higher")
    async def higher(self, interaction: Interaction, button: Button):
        if not await self.interaction_check(interaction):
            return
        
        await interaction.response.defer()

        user_id = interaction.user.id
        now = time.time()
        last_time = self.last_interaction.get(user_id, 0)
        if now - last_time < 2:
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are too fast, please wait a little bit...")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        self.last_interaction[user_id] = now

        async with self.lock:
            new_number = random.randint(1, 100)
            if new_number >= self.current:
                self.current = new_number
                if self.first_click:
                    self.first_click = False
                self.last_prediction = "higher"
                self.update_multipliers()
                self.embed = self.create_embed()
                self.click_count += 1
                if self.click_count >= self.max_clicks or self.total_multiplier >= 5.00:
                    for child in self.children:
                        if child.custom_id == "lower" or child.custom_id == "higher":
                            child.disabled = True
                return await interaction.followup.edit_message(message_id=interaction.message.id, embed=self.embed, view=self)
            else:
                await self.end_game(interaction, "higher", new_number)

    @discord.ui.button(label="Lower", style=ButtonStyle.red, custom_id="lower")
    async def lower(self, interaction: Interaction, button: Button):
        if not await self.interaction_check(interaction):
            return
        
        await interaction.response.defer()

        user_id = interaction.user.id
        now = time.time()
        last_time = self.last_interaction.get(user_id, 0)
        if now - last_time < 2:
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are too fast, please wait a little bit...")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        self.last_interaction[user_id] = now
        
        async with self.lock:
            new_number = random.randint(1, 100)
            if new_number <= self.current:
                self.current = new_number
                if self.first_click:
                    self.first_click = False
                self.last_prediction = "lower"
                self.update_multipliers()
                self.embed = self.create_embed()
                self.click_count += 1
                if self.click_count >= self.max_clicks or self.total_multiplier >= 5.00:
                    for child in self.children:
                        if child.custom_id == "lower" or child.custom_id == "higher":
                            child.disabled = True
                return await interaction.followup.edit_message(message_id=interaction.message.id, embed=self.embed, view=self)
            else:
                await self.end_game(interaction, "lower", new_number)

    @discord.ui.button(label="Cashout", style=ButtonStyle.blurple, custom_id="cashout")
    async def cashout(self, interaction: Interaction, button: Button):
        if not await self.interaction_check(interaction):
            return
        
        await interaction.response.defer()

        user_id = interaction.user.id
        now = time.time()
        last_time = self.last_interaction.get(user_id, 0)
        if now - last_time < 2:
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are too fast, please wait a little bit...")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        self.last_interaction[user_id] = now
        
        async with self.lock:
            if self.first_click:
                return await interaction.warn("You can't cashout before making a prediction", ephemeral=True)
            winnings = self.amount * self.total_multiplier
            await self.bot.db.execute("UPDATE economy SET cash = cash + $1 WHERE user_id = $2", winnings, self.ctx.author.id)
            await self.quests.add_win_game(interaction.user, "higherlower")
            await self.quests.add_win_money(interaction.user, "higherlower", Decimal(winnings) - Decimal(self.amount))
            await self.economy.logging(interaction.user, Decimal(winnings) - Decimal(self.amount), "won", "higherlower")
            await interaction.approve(f"Congratulations! You won **{winnings:,.2f}** {self.cash}")
            self.stop()
            for child in self.children:
                child.disabled = True
            return await interaction.followup.edit_message(message_id=interaction.message.id, embed=self.embed, view=self)

    async def end_game(self, interaction: Interaction, predicted_direction, new_number):
        if (predicted_direction == "higher" and self.current <= self.number) or (predicted_direction == "lower" and self.current >= self.number):
            await self.economy.logging(interaction.user, self.amount, "lost", "higherlower")
            await interaction.error(f"You lost **{self.bot.misc.humanize_number(self.amount)}** {self.cash}.\n> Old number: **{self.number}** | New number: **{new_number}** | You predicted: **{predicted_direction}**")
        else:
            return
        self.stop()
        for child in self.children:
            child.disabled = True
        return await interaction.followup.edit_message(message_id=interaction.message.id, embed=self.embed, view=self)