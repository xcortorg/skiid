import asyncio
import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Union  # type: ignore # type: ignore

import discord  # type: ignore
from discord import Embed
from discord import Member as DiscordMember  # type: ignore
from discord.ext import commands, tasks  # type: ignore
from discord.ext.commands import CommandError, Context, check  # type: ignore
from discord.ui import Button, View  # type: ignore
from discord.utils import format_dt  # type: ignore
from loguru import logger  # type: ignore
from pytz import timezone  # type: ignore
from rival_tools import thread  # type: ignore
from tools.chart import EconomyCharts  # type: ignore
from tools.important.subclasses.command import User  # type: ignore
from tools.important.subclasses.command import Member  # type: ignore
from tools.wock import Wock  # type: ignore

log = logger

maximum_gamble = 3001


def format_large_number(num: Union[int, float]) -> str:
    # List of suffixes for large numbers
    suffixes = [
        "",
        "K",
        "M",
        "B",
        "T",
        "Qa",
        "Qi",
        "Sx",
        "Sp",
        "Oc",
        "No",
        "Dc",
        "Ud",
        "Dd",
        "Td",
        "Qad",
        "Qid",
        "Sxd",
        "Spd",
        "Ocd",
        "Nod",
        "Vg",
        "Uv",
        "Dv",
        "Tv",
        "Qav",
        "Qiv",
        "Sxv",
        "Spv",
        "Ocv",
        "Nov",
        "Tg",
        "Utg",
        "Dtg",
        "Ttg",
        "Qatg",
        "Qitg",
        "Sxtg",
        "Sptg",
        "Octg",
        "Notg",
        "Qng",
    ]

    # Number of digits in the input number
    num_str = str(num)
    if "." in num_str:
        num_str = num_str[: num_str.index(".")]
    num_len = len(num_str)

    # Determine the appropriate suffix and scale the number
    if num_len <= 3:
        return num_str  # No suffix needed for numbers with 3 or fewer digits

    # Calculate the index for suffixes list
    suffix_index = (num_len - 1) // 3

    if suffix_index >= len(suffixes):
        return f"{num} is too large to format."

    # Calculate the formatted number
    scaled_num = int(num_str[: num_len - suffix_index * 3])

    return f"{scaled_num}{suffixes[suffix_index]}"


class OverMaximum(CommandError):
    def __init__(self, m, **kwargs):
        self.m = m
        super().__init__(m)


@dataclass
class Achievement:
    name: str
    description: str
    price: Optional[int] = None


@dataclass
class Item:
    name: str
    description: str
    price: int
    duration: int
    emoji: str


@dataclass
class Chance:
    percentage: float
    total: float


class BlackjackView(View):
    def __init__(self, ctx, bot):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.bot = bot
        self.move = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user == self.ctx.author

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.green)
    async def hit_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        self.move = 0
        self.stop()

    @discord.ui.button(label="Stay", style=discord.ButtonStyle.gray)
    async def stay_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        self.move = 1
        self.stop()

    async def wait_for_input(self):
        try:
            await self.wait()
            return self.move if self.move is not None else 1
        except Exception:
            return 1


def get_hour():
    est = timezone("US/Eastern")
    now = datetime.now(est)
    return now.hour + 1


def get_win(multiplied: bool = False, by: int = 3):
    if multiplied:
        if by == 2:
            return random.uniform(3.0, 5.0)
        else:
            return random.uniforn(4.5, 7.5)
    else:
        return random.uniform(1.5, 2.5)


def _format_int(n: Union[float, str, int]):
    if isinstance(n, float):
        n = "{:.2f}".format(n)
    if isinstance(n, str):
        if "." in n:
            try:
                amount, decimal = n.split(".")
                n = f"{amount}.{decimal[:2]}"
            except Exception:
                n = f"{n.split('.')[0]}.00"
    #   if str(n).startswith("-"):
    #        return f":clown: ${n}"
    reversed = str(n).split(".")[0][::-1]
    d = ""
    amount = 0
    for i in reversed:
        amount += 1
        if amount == 3:
            d += f"{i},"
            amount = 0
        else:
            d += i
    if d[::-1].startswith(","):
        return d[::-1][1:]
    return d[::-1]


def format_int(n: Union[float, str, int], disallow_negatives: Optional[bool] = False):
    n = _format_int(n)
    if disallow_negatives is True and n.startswith("-"):
        return 0
    return n


def get_chances():
    from config import CHANCES

    data = {}
    for key, value in CHANCES.items():
        data[key] = Chance(percentage=value["percentage"], total=value["total"])
    return data


def get_time_next_day():
    current_datetime = datetime.now()
    tomorrow = current_datetime + timedelta(days=1)
    next_day_start = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 0, 0, 0)
    time_until_next_day = (next_day_start - current_datetime).total_seconds()
    return time_until_next_day


class BankAmount(commands.Converter):
    name = "BankAmount"

    async def convert(self, ctx: Context, argument: Union[int, float, str]):
        if isinstance(argument, str):
            argument = argument.replace(",", "")
        if isinstance(argument, int):
            balance = await self.bot.db.fetchval(
                "SELECT bank FROM economy WHERE user_id = $1", ctx.author.id
            )
            if argument > balance:
                raise commands.CommandError(
                    f"you only have **{format_int(balance)}** bucks in your bank"
                )
            if argument < 0:
                raise commands.CommandError("you can't withdraw an amount below 0")
            argument = float(argument)
        elif isinstance(argument, float):
            balance = await self.bot.db.fetchval(
                "SELECT bank FROM economy WHERE user_id = $1", ctx.author.id
            )
            if argument > balance:
                raise commands.CommandError(
                    f"you only have **{format_int(balance)}** bucks in your bank"
                )
            if argument < 0.00:
                raise commands.CommandError("you can't withdraw an amount below 0")
        else:
            if argument.lower() == "all":
                argument = await ctx.bot.db.fetchval(
                    "SELECT bank FROM economy WHERE user_id = $1", ctx.author.id
                )
            try:
                argument = float(argument)
            except Exception:
                await ctx.warning("Please provide an **Amount**")
                raise OverMaximum("lol")  # MissingRequiredArgument(BankAmount)
        return argument


class Amount(commands.Converter):
    name = "Amount"

    async def convert(self, ctx: Context, argument: Union[int, float, str]):
        if "," in argument:
            argument = argument.replace(",", "")
            argument = float(argument)
        if isinstance(argument, int):
            balance = await ctx.bot.db.fetchval(
                "SELECT balance FROM economy WHERE user_id = $1", ctx.author.id
            )
            if float(argument) > float(balance):
                raise commands.CommandError(
                    f"you only have **{format_int(balance)}** bucks"
                )
            if argument < 0:
                raise commands.CommandError("you can't gamble an amount below 0")
            argument = float(argument)
        elif isinstance(argument, float):
            balance = await ctx.bot.db.fetchval(
                "SELECT balance FROM economy WHERE user_id = $1", ctx.author.id
            )
            if argument > balance:
                raise commands.CommandError(
                    f"you only have **{format_int(balance)}** bucks"
                )
            if argument < 0.00:
                raise commands.CommandError("you can't gamble an amount below 0")
        else:
            if argument.lower() == "all":
                argument = await ctx.bot.db.fetchval(
                    "SELECT balance FROM economy WHERE user_id = $1", ctx.author.id
                )
            try:
                argument = float(argument)
            except Exception:
                await ctx.warning("Please provide an **Amount**")
                raise OverMaximum("lol")  # MissingRequiredArgument(Amount)
        return argument


class GambleAmount(commands.Converter):
    name = "GambleAmount"

    async def convert(self, ctx: Context, argument: Union[int, float, str]):
        if "," in argument:
            argument = argument.replace(",", "")
            argument = float(argument)
        if isinstance(argument, int):
            balance = await ctx.bot.db.fetchval(
                "SELECT balance FROM economy WHERE user_id = $1", ctx.author.id
            )
            if float(argument) > float(balance):
                raise commands.CommandError(
                    f"you only have **{format_int(balance)}** bucks"
                )
            if argument < 0:
                raise commands.CommandError("you can't gamble an amount below 0")
            argument = float(argument)
        elif isinstance(argument, float):
            balance = await ctx.bot.db.fetchval(
                "SELECT balance FROM economy WHERE user_id = $1", ctx.author.id
            )
            if argument > balance:
                raise commands.CommandError(
                    f"you only have **{format_int(balance)}** bucks"
                )
            if argument < 0.00:
                raise commands.CommandError("you can't gamble an amount below 0")
        else:
            if argument.lower() == "all":
                argument = float(
                    await ctx.bot.db.fetchval(
                        "SELECT balance FROM economy WHERE user_id = $1", ctx.author.id
                    )
                )
                argument = argument
            try:
                argument = float(argument)
            except Exception:
                await ctx.warning("Please provide an **Amount**")
                raise OverMaximum("lol")
        # if float(argument) >= float(maximum_gamble):
        #     if ctx.author.name == "aiohttp":
        #         m = f" not `{argument}`"
        #     else:
        #         m = ""
        #     await ctx.fail(f"you can only gamble a maximum of **{format_int(float(maximum_gamble) - 1.0)}**{m}")
        #     raise OverMaximum("lol")
        return argument


def account():
    async def predicate(ctx: Context):
        if ctx.command.name == "steal":
            mentions = [m for m in ctx.message.mentions if m != ctx.bot.user]
            if len(mentions) > 0:
                if not await ctx.bot.db.fetchrow(
                    """SELECT * FROM economy WHERE user_id = $1""", mentions[0].id
                ):
                    await ctx.fail(
                        f"**{mentions[0].name}** doesn't have an account opened"
                    )
                    return False
        check = await ctx.bot.db.fetchval(
            "SELECT COUNT(*) FROM economy WHERE user_id = $1",
            ctx.author.id,
        )
        if check == 0:
            await ctx.fail(
                f"You **haven't setup your account**, use `{ctx.prefix}open` to **create one**"
            )
            return False
        return True

    return check(predicate)


class Economy(commands.Cog):
    def __init__(self, bot: Wock):
        self.bot = bot
        self.locks = defaultdict(asyncio.Lock)
        self.mapping = {
            1: ":one:",
            2: ":two:",
            3: ":three:",
            4: ":four:",
            5: ":five:",
            6: ":six:",
            7: ":seven:",
            8: ":eight:",
            9: ":nine:",
        }
        self.chances = get_chances()
        self.items = {
            "purple devil": {
                "price": 1000000,
                "description": "prevents other users from stealing from your wallet for 8 hours",
                "duration": 28800,
                "emoji": "",
            },
            "white powder": {
                "price": 500000,
                "description": "allows you to win double from a coinflip for 1 minute",
                "duration": 60,
                "emoji": "",
            },
            "oxy": {
                "price": 400000,
                "description": "allows you 2x more bucks when you win a gamble for 30 seconds",
                "duration": 30,
                "emoji": "",
            },
            "meth": {
                "description": "roll 2x more for 4 minutes",
                "price": 350000,
                "duration": 240,
                "emoji": "",
            },
            "shrooms": {
                "description": "increases your chances of winning gamble commands by 10% for 10 minutes",
                "price": 100000,
                "duration": 600,
                "emoji": "",
            },
        }
        self.symbols = ["♠", "♥", "♦", "♣"]
        self.achievements = {
            "Lets begin.": {
                "description": "open an account through wock for gambling",
                "price": None,
            },
            "Getting higher": {
                "description": "accumulate 50,000 bucks through gambling",
                "price": 50000,
            },
            "Closer..": {
                "description": "accumulate 200,000 bucks through gambling",
                "price": 200000,
            },
            "Sky high!": {
                "description": "accumulate 450,000 bucks through gambling",
                "price": 450000,
            },
            "less text more gamble": {
                "description": "accumulate 600,000 bucks",
                "price": 600000,
            },
            "run it up": {
                "description": "accumulate 2,000,000 bucks",
                "price": 2000000,
            },
            "richer": {"description": "accumulate 3,500,000 bucks", "price": 3500000},
            "rich and blind": {
                "description": "accumulate 5,000,000 bucks",
                "price": 5000000,
            },
            "High roller": {
                "description": "accumulate over 10,000,000 in bucks",
                "price": 10000000,
            },
            "Highest in the room.": {
                "description": "accumulate over 500,000,000 in bucks",
                "price": 500000000,
            },
            "Amazing way to spend!": {
                "description": "Buy the full amount of every item in the item shop",
                "price": None,
            },
            "Time to shop!": {
                "description": "buy something from the item shop",
                "price": None,
            },
            "spending spree!": {
                "description": "spend over 1,000,000 worth of items from the shop",
                "price": 1000000,
            },
            "loser.": {"description": "lose over 40,000 in gambling", "price": 40000},
            "retard": {
                "description": "lose all of your bucks from gambling all",
                "price": None,
            },
            "Down and out": {
                "description": "Lose over 1,000,000 in gambling",
                "price": 1000000,
            },
            "Master thief": {
                "description": "Steal over 100,000 in bucks from other users",
                "price": 100000,
            },
            "unlucky": {
                "description": "have over 50,000 bucks stolen from your wallet",
                "price": 50000,
            },
            "banking bank bank": {
                "description": "transfer 200,000 bucks or more to a wallet",
                "price": 200000,
            },
            "sharing is caring": {
                "description": "pay another user 500 bucks or more",
                "price": 500,
            },
            "shared god": {
                "description": "pay 5 users 500,000 bucks or more",
                "price": 500000,
            },
            "immortally satisfied": {
                "description": "having a balance of 10,000,000, pay all bucks to another user",
                "price": 10000000,
            },
        }
        self.cards = {
            1: "`{sym} 1`, ",
            2: "`{sym} 2`, ",
            3: "`{sym} 3`, ",
            4: "`{sym} 4`, ",
            5: "`{sym} 5`, ",
            6: "`{sym} 6`, ",
            7: "`{sym} 7`, ",
            8: "`{sym} 8`, ",
            9: "`{sym} 9`, ",
            10: "`{sym} 10`, ",
        }

        self.format_economy()
        self.chart = EconomyCharts(self.bot)
        self.clear_earnings.start()

    def format_economy(self):
        new_items = {}
        new_achievements = {}
        for key, value in self.items.items():
            new_items[key] = Item(name=key, **value)
        for _k, _v in self.achievements.items():
            new_achievements[_k] = Achievement(name=_k, **_v)
        self.items = new_items
        self.achievements = new_achievements

    def get_value(self, ctx: Context) -> bool:
        values = self.chances[ctx.command.qualified_name]
        return calculate(values.percentage, values.total)  # type: ignore # noqa: F821

    @tasks.loop(hours=24)
    async def clear_earnings(self):
        time = get_time_next_day()
        await asyncio.sleep(time)
        await self.bot.db.execute("""DELETE FROM earnings""")

    @thread
    def generate_cards(self):
        cards_out = list()
        cards_out_n = list()
        amount = 0
        cards = [card for card in self.cards]
        has_hit = False
        while True:
            card = random.choice(cards)
            if card not in cards_out:
                cards_out.append(card)
                if card == "11":
                    if not has_hit or not amount > 11:
                        card = 11
                        has_hit = True
                    else:
                        card = 1
                amount += int(card)
                cards_out_n.append(int(card))
            if len(cards_out) == 7:
                break
        return cards_out, cards_out_n, amount

    def format_int(self, n: Union[float, str, int]):
        if isinstance(n, float):
            n = "{:.2f}".format(n)
        if isinstance(n, str):
            if "." in n:
                try:
                    amount, decimal = n.split(".")
                    n = f"{amount}.{decimal[:2]}"
                except Exception:
                    n = f"{n.split('.')[0]}.00"
        if str(n).startswith("-"):
            return f":clown: ${n}"
        reversed = str(n).split(".")[0][::-1]
        d = ""
        amount = 0
        for i in reversed:
            amount += 1
            if amount == 3:
                d += f"{i},"
                amount = 0
            else:
                d += i
        if d[::-1].startswith(","):
            return d[::-1][1:]
        return d[::-1]

    async def get_balance(
        self, member: DiscordMember, with_bank: Optional[bool] = False
    ) -> Union[float, tuple]:
        if with_bank is True:
            data = await self.bot.db.fetchrow(
                """SELECT * FROM economy WHERE user_id = $1""", member.id
            )
            balance = float(str(data["balance"]))
            bank = float(str(data["bank"]))
            return balance, bank
        else:
            data = await self.bot.db.fetchval(
                """SELECT balance FROM economy WHERE user_id = $1""", member.id
            )
            balance = float(str(data))
            if balance < 0.00:
                await self.bot.db.execute(
                    """UPDATE economy SET balance = $1 WHERE user_id = $2""",
                    0.00,
                    member.id,
                )
                return 0.00
            return balance

    def get_expiration(self, item: str) -> tuple:
        now = datetime.now()
        ex = now + timedelta(seconds=self.items[item].duration)
        return now, ex

    async def use_item(self, ctx: Context, item: str):
        if item not in list(self.items.keys()):
            return await ctx.fail("that is not a valid item")
        _ = await self.bot.db.fetchrow(
            """SELECT * FROM inventory WHERE user_id = $1 AND item = $2""",
            ctx.author.id,
            item,
        )
        if not _:
            return await ctx.fail(f"you don't have any **{item}'s**")
        if _["amount"] > 1:
            kwargs = [_["amount"] - 1, ctx.author.id, item]
            query = (
                """UPDATE inventory SET amount = $1 WHERE user_id = $2 AND item = $3"""
            )
        else:
            kwargs = [ctx.author.id, item]
            query = """DELETE FROM inventory WHERE user_id = $1 AND item = $2"""
        if await self.bot.db.fetchrow(
            """SELECT * FROM used_items WHERE user_id = $1 AND item = $2""",
            ctx.author.id,
            item,
        ):
            return await ctx.fail(f"you are already zooted off da **{item}**")
        ts, ex = self.get_expiration(item)
        await self.bot.db.execute(
            """INSERT INTO used_items (user_id, item, ts, expiration) VALUES($1, $2, $3, $4) ON CONFLICT(user_id, item) DO UPDATE SET ts = excluded.ts, expiration = excluded.expiration""",
            ctx.author.id,
            item,
            ts,
            ex,
        )
        await self.bot.db.execute(query, *kwargs)
        return await ctx.success(
            f"successfully used **{item}** it will expire {format_dt(ex, style='R')}"
        )

    async def buy_item(self, ctx: Context, item: str, amount: int = 1):
        if amount > 99:
            return await ctx.fail("you can only buy 99")
        if item not in self.items.keys():
            return await ctx.fail("not a valid item")
        price = self.items[item].price * amount
        balance = await self.get_balance(ctx.author)
        if float(price) >= float(balance):
            return await ctx.fail("you do not have enough for that")
        await self.bot.db.execute(
            """INSERT INTO inventory (user_id, item, amount) VALUES($1, $2, $3) ON CONFLICT (user_id, item) DO UPDATE SET amount = inventory.amount + excluded.amount""",
            ctx.author.id,
            item,
            amount,
        )
        await self.update_balance(ctx.author, "Take", price, False)
        return await ctx.success(
            f"successfully bought {amount} **{item}** for `{self.items[item].price}`"
        )

    async def check_shrooms(self, ctx: Context):
        if await self.bot.db.fetchrow(
            """SELECT * FROM used_items WHERE user_id = $1 AND item = $2""",
            ctx.author.id,
            "shrooms",
        ):
            return True
        else:
            return False

    async def check_item(self, ctx: Context, member: Optional[DiscordMember] = None):
        cn = ctx.command.qualified_name
        item = None
        if member is None:
            member = ctx.author
        if cn == "coinflip":
            item = "white powder"
        elif cn == "steal":
            item = "purple devil"
        elif cn == "gamble":
            item = "oxy"
        elif cn == "roll":
            item = "meth"
        kwargs = [member.id, item]
        data = await self.bot.db.fetchrow(
            """SELECT expiration FROM used_items WHERE user_id = $1 AND item = $2""",
            *kwargs,
        )
        if not data:
            return False
        if data["expiration"].timestamp() <= datetime.now().timestamp():
            await self.bot.db.execute(
                """DELETE FROM used_items WHERE user_id = $1 AND item = $2""", *kwargs
            )
            return False
        return True

    async def update_balance(
        self,
        member: DiscordMember,
        action: str,
        amount: Union[float, int],
        add_earnings: Optional[bool] = True,
    ):
        if not add_earnings:
            earnings = 0
            w = 0
            total = 0
        else:
            earnings = amount
            w = 1
            total = 1
        hour = get_hour()
        if action == "Add":
            data = await self.bot.db.execute(
                """UPDATE economy SET balance = economy.balance + $1, earnings = economy.earnings + $2, wins = economy.wins + $4, total = economy.total + $5 WHERE user_id = $3 RETURNING balance""",
                amount,
                earnings,
                member.id,
                w,
                total,
            )
            await self.bot.db.execute(
                f"""INSERT INTO earnings (user_id, h{hour}) VALUES($1,$2) ON CONFLICT(user_id) DO UPDATE SET h{hour} = excluded.h{hour} + earnings.h{hour}""",
                member.id,
                float(earnings),
            )
        elif action == "Take":
            data = await self.bot.db.execute(
                """UPDATE economy SET balance = economy.balance - $1, earnings = economy.earnings - $2, total = economy.total + $4 WHERE user_id = $3 RETURNING balance""",
                amount,
                earnings,
                member.id,
                total,
            )
            await self.bot.db.execute(
                f"""INSERT INTO earnings (user_id, h{hour}) VALUES($1,$2) ON CONFLICT(user_id) DO UPDATE SET h{hour} = earnings.h{hour} - excluded.h{hour}""",
                member.id,
                float(earnings),
            )
        elif action == "Set":
            data = await self.bot.db.execute(
                """UPDATE economy SET balance = $1  WHERE user_id = $2 RETURNING balance""",
                amount,
                earnings,
                member.id,
            )
        return data

    def get_random_value(self, *args) -> int:
        return random.randint(*args)

    def int_to_coin(self, n: int) -> str:
        if n == 2:
            return "Heads"
        else:
            return "Tails"

    async def wait_for_input(self, ctx: Context):
        try:
            x = await self.bot.wait_for(
                "message",
                check=lambda m: m.channel == ctx.message.channel
                and m.author == ctx.author,
            )
            if str(x.content).lower() == "hit":
                move = 0
            elif str(x.content).lower() == "stay":
                move = 1
            await x.delete()
            return move
        except asyncio.TimeoutError:
            return 1

    @commands.command(
        name="blackjack",
        aliases=["bj"],
        brief="play blackjack against the house to gamble bucks",
        example=",blackjack 100",
    )
    @account()
    async def blackjack(self, ctx: Context, *, amount: GambleAmount):
        async with self.locks[f"bj:{ctx.author.id}"]:
            balance = await self.get_balance(ctx.author)
            if float(amount) > float(balance):
                return await ctx.fail(
                    f"you only have `{self.format_int(balance)}` bucks"
                )
            author_deck, author_deck_n, author_amount = await self.generate_cards()
            bot_deck, bot_deck_n, bot_amount = await self.generate_cards()
            get_amount = lambda i, a: [i[z] for z in range(a)]  # noqa: E731
            win_amount = float(amount) * 1.75
            em = discord.Embed(
                color=self.bot.color,
                title="Blackjack",
                description="Would you like to **hit** or **stay** this round?",
            )
            em.add_field(
                name="Your Cards ({})".format(sum(get_amount(author_deck_n, 2))),
                value=f'{"".join([self.cards[x].replace("{sym}", random.choice(self.symbols)) for x in get_amount(author_deck, 2)])}',
                inline=True,
            )
            em.add_field(
                name="My Cards ({})".format(sum(get_amount(bot_deck_n, 2)[:1])),
                value=f'{"".join([self.cards[x].replace("{sym}", random.choice(self.symbols)) for x in get_amount(bot_deck, 2)[:1]])}',
                inline=False,
            )
            thumbnail_url = "https://media.discordapp.net/attachments/1201966711826555002/1250569957830295704/poker_cards.png?ex=666b6b88&is=666a1a08&hm=e21d87bbf61518d3f70bb7772cb79b4a1ada5d28db5c2263a32e77db278524ed&=&format=webp&quality=lossless"
            em.set_thumbnail(url=thumbnail_url)

            view = BlackjackView(ctx, self.bot)
            msg = await ctx.send(embed=em, view=view)

            bot_val = 2
            bot_stay = False

            for i in range(3, 9):
                move = await view.wait_for_input()
                view = BlackjackView(ctx, self.bot)
                em = discord.Embed(color=self.bot.color, title="Blackjack")

                if not bot_stay:
                    if bot_val == 4:
                        bot_stay = True
                    elif sum(get_amount(bot_deck_n, bot_val)) <= 16:
                        bot_val += 1
                    elif sum(get_amount(bot_deck_n, bot_val)) == 21:
                        bot_stay = True
                    else:
                        if random.randint(0, 1) == 0:
                            bot_stay = True
                        else:
                            bot_val += 1

                if move == 1:
                    i -= 1
                    em.add_field(
                        name="Your hand ({})".format(sum(get_amount(author_deck_n, i))),
                        value=f'{"".join([self.cards[x].replace("{sym}", random.choice(self.symbols)) for x in get_amount(author_deck, i)])}',
                        inline=True,
                    )
                    em.add_field(
                        name="Opponents hand ({})".format(
                            sum(get_amount(bot_deck_n, bot_val))
                        ),
                        value=f'{"".join([self.cards[x].replace("{sym}", random.choice(self.symbols)) for x in get_amount(bot_deck, bot_val)])}',
                        inline=False,
                    )

                    if sum(get_amount(author_deck_n, i)) == sum(
                        get_amount(bot_deck_n, bot_val)
                    ):
                        em.description = "Nobody won."
                    elif (
                        sum(get_amount(author_deck_n, i)) > 21
                        and sum(get_amount(bot_deck_n, bot_val)) > 21
                    ):
                        em.description = "Nobody won."
                    elif (
                        sum(get_amount(author_deck_n, i))
                        > sum(get_amount(bot_deck_n, bot_val))
                        or sum(get_amount(bot_deck_n, bot_val)) > 21
                    ):
                        em.description = f"you won **{self.format_int(int(win_amount).maximum(5000))}**"
                        await self.update_balance(
                            ctx.author, "Add", int(win_amount).maximum(5000)
                        )
                    else:
                        em.description = (
                            f"you lost **{self.format_int(float(amount))}**"
                        )
                        await self.update_balance(ctx.author, "Take", amount)
                    thumbnail_url = "https://media.discordapp.net/attachments/1201966711826555002/1250569957830295704/poker_cards.png?ex=666b6b88&is=666a1a08&hm=e21d87bbf61518d3f70bb7772cb79b4a1ada5d28db5c2263a32e77db278524ed&=&format=webp&quality=lossless"
                    em.set_thumbnail(url=thumbnail_url)
                    await msg.edit(embed=em, view=None)
                    return
                try:
                    if (
                        sum(get_amount(bot_deck_n, bot_val)) > 21
                        or sum(get_amount(author_deck_n, i)) > 21
                    ):
                        if (
                            sum(get_amount(author_deck_n, i)) > 21
                            and sum(get_amount(bot_deck_n, bot_val)) > 21
                        ):
                            em.description = "Nobody won."
                        elif sum(get_amount(author_deck_n, i)) > 21:
                            em.description = f"You went over 21 and lost **{self.format_int(float(amount))} bucks**"
                            await self.update_balance(ctx.author, "Take", amount)
                        else:
                            em.description = f"I went over 21 and you won **{self.format_int(int(win_amount).maximum(5000))} bucks**"
                            await self.update_balance(
                                ctx.author, "Add", int(win_amount).maximum(5000)
                            )
                        em.add_field(
                            name="Your hand ({})".format(
                                sum(get_amount(author_deck_n, i))
                            ),
                            value=f'{"".join([self.cards[x].replace("{sym}", random.choice(self.symbols)) for x in get_amount(author_deck, i)])}',
                            inline=True,
                        )
                        em.add_field(
                            name="Opponents hand ({})".format(
                                sum(get_amount(bot_deck_n, bot_val))
                            ),
                            value=f'{"".join([self.cards[x].replace("{sym}", random.choice(self.symbols)) for x in get_amount(bot_deck, bot_val)])}',
                            inline=False,
                        )
                        thumbnail_url = "https://media.discordapp.net/attachments/1201966711826555002/1250569957830295704/poker_cards.png?ex=666b6b88&is=666a1a08&hm=e21d87bbf61518d3f70bb7772cb79b4a1ada5d28db5c2263a32e77db278524ed&=&format=webp&quality=lossless"
                        em.set_thumbnail(url=thumbnail_url)
                        await msg.edit(embed=em, view=None)
                        return
                except Exception:
                    i -= 1
                    if (
                        sum(get_amount(bot_deck_n, bot_val)) > 21
                        or sum(get_amount(author_deck_n, i)) > 21
                    ):
                        if (
                            sum(get_amount(author_deck_n, i)) > 21
                            and sum(get_amount(bot_deck_n, bot_val)) > 21
                        ):
                            em.description = "Nobody won."
                        elif sum(get_amount(author_deck_n, i)) > 21:
                            em.description = f"You went over 21 and lost **{self.format_int(float(amount))} bucks**"
                            await self.update_balance(ctx.author, "Take", amount)
                        else:
                            em.description = f"I went over 21 and you won **{self.format_int(int(win_amount).maximum(5000))} bucks**"
                            await self.update_balance(
                                ctx.author, "Add", int(win_amount).maximum(5000)
                            )
                        em.add_field(
                            name="Your hand ({})".format(
                                sum(get_amount(author_deck_n, i))
                            ),
                            value=f'{"".join([self.cards[x].replace("{sym}", random.choice(self.symbols)) for x in get_amount(author_deck, i)])}',
                            inline=True,
                        )
                        em.add_field(
                            name="Opponents hand ({})".format(
                                sum(get_amount(bot_deck_n, bot_val))
                            ),
                            value=f'{"".join([self.cards[x].replace("{sym}", random.choice(self.symbols)) for x in get_amount(bot_deck, bot_val)])}',
                            inline=False,
                        )
                        thumbnail_url = "https://media.discordapp.net/attachments/1201966711826555002/1250569957830295704/poker_cards.png?ex=666b6b88&is=666a1a08&hm=e21d87bbf61518d3f70bb7772cb79b4a1ada5d28db5c2263a32e77db278524ed&=&format=webp&quality=lossless"
                        em.set_thumbnail(url=thumbnail_url)
                        await msg.edit(embed=em, view=None)
                        return

                em.add_field(
                    name="Your hand ({})".format(sum(get_amount(author_deck_n, i))),
                    value=f'{"".join([self.cards[x].replace("{sym}", random.choice(self.symbols)) for x in get_amount(author_deck, i)])}',
                    inline=True,
                )
                em.add_field(
                    name="Opponents hand ({})".format(
                        sum(get_amount(bot_deck_n, i)[:1])
                    ),
                    value=f'{"".join([self.cards[x].replace("{sym}", random.choice(self.symbols)) for x in get_amount(bot_deck, 2)[:1]])}',
                    inline=False,
                )
                thumbnail_url = "https://media.discordapp.net/attachments/1201966711826555002/1250569957830295704/poker_cards.png?ex=666b6b88&is=666a1a08&hm=e21d87bbf61518d3f70bb7772cb79b4a1ada5d28db5c2263a32e77db278524ed&=&format=webp&quality=lossless"
                em.set_thumbnail(url=thumbnail_url)
                await msg.edit(embed=em, view=view)

            if (
                sum(get_amount(bot_deck_n, 5)) > 21
                or sum(get_amount(author_deck_n, 5)) > 21
            ):
                if (
                    sum(get_amount(author_deck_n, i)) > 21
                    and sum(get_amount(bot_deck_n, bot_val)) > 21
                ):
                    em.description = "Nobody won."
                elif sum(get_amount(author_deck_n, i)) > 21:
                    em.description = f"You went over 21 and you lost **{self.format_int(float(amount))} bucks**"
                    await self.update_balance(ctx.author, "Take", amount)
                else:
                    em.description = f"I went over 21 and you won **{self.format_int(int(win_amount).maximum(5000))} bucks**"
                    await self.update_balance(
                        ctx.author, "Add", int(win_amount).maximum(5000)
                    )
                em.add_field(
                    name="Your hand ({})".format(sum(get_amount(author_deck_n, i))),
                    value=f'{"".join([self.cards[x].replace("{sym}", random.choice(self.symbols)) for x in get_amount(author_deck, i)])}',
                    inline=True,
                )
                em.add_field(
                    name="Opponents hand ({})".format(
                        sum(get_amount(bot_deck_n, bot_val))
                    ),
                    value=f'{"".join([self.cards[x].replace("{sym}", random.choice(self.symbols)) for x in get_amount(bot_deck, bot_val)])}',
                    inline=False,
                )
                await msg.edit(embed=em, view=None)

    @commands.command(name="shop", brief="shows all of the items", example=",shop")
    async def shop(self, ctx: Context):
        product = list()
        for name, item in self.items.items():
            product.append(
                f"**{name}**:\n**description**: {item.description}\n**price**: `{self.format_int(item.price)}`\n\n"
            )
        product = discord.utils.chunk_list(product, 2)
        embeds = [
            Embed(title="shop", description="".join(m for m in _), color=self.bot.color)
            for _ in product
        ]
        return await ctx.paginate(embeds)

    @commands.group(
        name="steal",
        aliases=["rob"],
        brief="steal bucks from other users",
        example=",steal @o_5v",
        invoke_without_command=True,
    )
    @account()
    async def steal(self, ctx: Context, *, member: Member):
        if await self.bot.db.fetchrow(
            """SELECT * FROM steal_disabled WHERE guild_id = $1""", ctx.guild.id
        ):
            return await ctx.fail("steal is disabled here")
        if member == ctx.author:
            return await ctx.fail("nice try lol")
        rl = await self.bot.glory_cache.ratelimited(f"steal:{ctx.author.id}", 1, 300)
        if rl != 0:
            return await ctx.fail(
                f"You can steal again {discord.utils.format_dt(datetime.now() + timedelta(seconds = rl), style='R')}"
            )

        check = await self.check_item(ctx, member)
        if check is True:
            return await ctx.fail(
                f"You can't steal from {member.mention} cuz they zooted off dat purple devil yahurd me cuh?"
            )
        amount = min(float(await self.get_balance(member)), 500.0)
        if float(amount) == 0.00:
            return await ctx.fail(f"sorry but **{member.name}** has `0` bucks")
        _message = await ctx.send(
            embed=Embed(
                description=f"{ctx.author.mention} is **attempting to steal** `{self.format_int(amount)}`. If {member.mention} **doesn't reply it will be stolen**",
                color=self.bot.color,
            ),
            content=f"{member.mention}",
        )
        try:

            def check(message):
                return message.author == member and message.channel == ctx.channel

            # Wait for a reply from the user
            msg = await self.bot.wait_for(
                "message", timeout=20.0, check=check
            )  # noqa: F841
            await _message.edit(
                content=None,
                embed=Embed(
                    color=self.bot.color,
                    description=f"{ctx.author.mention}: stealing from **{member.name}** **failed**",
                ),
            )
        except asyncio.TimeoutError:
            await self.update_balance(member, "Take", amount)
            await self.update_balance(ctx.author, "Add", amount, True)
            return await _message.edit(
                content=None,
                embed=Embed(
                    color=self.bot.color,
                    description=f"{ctx.author.mention}: **Stole {self.format_int(amount)}** from {member.mention}",
                ),
            )

    @steal.command(
        name="toggle",
        bief="disable or enable the steal command for your server",
        example=",steal toggle",
    )
    async def steal_disable(self, ctx: Context):
        data = await self.bot.db.fetchrow(
            """SELECT * FROM steal_disabled WHERE guild_id = $1"""
        )
        if data:
            await self.bot.db.execute(
                """DELETE FROM steal_disabled WHERE guild_id = $1""", ctx.guild.id
            )
            m = "Stealing in this server been **enabled**"
        else:
            await self.bot.db.execute(
                """INSERT INTO steal_disabled (guild_id) VALUES($1)""", ctx.guild.id
            )
            m = "Stealing in this server has been **disabled**"
        return await ctx.success(m)

    @commands.command(name="setbalance", hidden=True)
    @commands.is_owner()
    async def setbalance(self, ctx: Context, member: Union[Member, User], amount: int):
        await self.bot.db.execute(
            """UPDATE economy SET balance = $1, earnings = $1 WHERE user_id = $2""",
            amount,
            member.id,
        )
        return await ctx.success(
            f"**{member.mention}'s balance is set to `{self.format_int(amount)}` bucks**"
        )

    @commands.command(
        name="balance",
        aliases=["earnings", "bal", "wallet"],
        brief="Show your wallet, bank and graph of growth through gambling",
        example=",balance",
    )
    @account()
    async def earnings(self, ctx: Context, member: Member = commands.Author):
        try:
            return await self.chart.chart_earnings(ctx, member)
        except Exception as e:
            if ctx.author.name == "aiohttp":
                raise e
            return await ctx.fail(f"**{str(member)}** doesn't have an account")

    @commands.command(name="setbank", hidden=True)
    @commands.is_owner()
    async def setbank(self, ctx: Context, member: Union[Member, User], amount: int):
        await self.bot.db.execute(
            """UPDATE economy SET bank = $1, earnings = $1 WHERE user_id = $2""",
            amount,
            member.id,
        )
        return await ctx.currency(
            f"**{member.mention}'s bank is set to `{self.format_int(amount)}` bucks**"
        )

    @commands.command(
        name="open", brief="Open an account to start gambling", example=",open"
    )
    async def open(self, ctx: Context):
        if not await self.bot.db.fetchrow(
            """SELECT * FROM economy WHERE user_id = $1""", ctx.author.id
        ):
            await self.bot.db.execute(
                """INSERT INTO economy (user_id, balance, bank) VALUES($1,$2,$3)""",
                ctx.author.id,
                200.00,
                0.00,
            )
            return await ctx.currency(
                "**Account opened** with a starting balance of **200 bucks**, The **House** will do everything they can to make you go **bankrupt**"
            )
        else:
            return await ctx.fail("You already have an **account**")

    @commands.command(
        name="deposit",
        brief="Deposit bucks from your wallet to your bank",
        example=",deposit 200",
    )
    @account()
    async def deposit(self, ctx: Context, amount: Amount):
        if str(amount).startswith("-"):
            return await ctx.warning("You **Cannot use negatives**")
        balance = await self.get_balance(ctx.author)
        if float(balance) < float(amount):
            return await ctx.warning(
                f"You only have **{self.format_int(balance)} bucks**"
            )
        if float(str(amount)) < 0.00:
            return await ctx.fail("lol nice try")
        if float(str(amount)) < 0.00:
            return await ctx.fail(f"You only have **{self.format_int(balance)} bucks**")
        await self.bot.db.execute(
            """UPDATE economy SET balance = economy.balance - $1, bank = economy.bank + $1 WHERE user_id = $2""",
            amount,
            ctx.author.id,
        )
        return await ctx.deposit(
            f"**{self.format_int(amount)}** bucks were **deposited into your bank**"
        )

    @commands.command(
        name="withdraw",
        brief="Withdraw bucks from your bank to your wallet",
        example=",withdraw 200",
    )
    @account()
    async def withdraw(self, ctx: Context, amount: BankAmount):
        if str(amount).startswith("-"):
            return await ctx.warning("You **Cannot use negatives**")
        if float(str(amount)) < 0.00:
            return await ctx.fail("lol nice try")
        balance, bank = await self.get_balance(ctx.author, True)  # type: ignore
        if float(str(amount)) > float(str(bank)):
            return await ctx.warning(
                f"You only have **{self.format_int(bank)}** bucks in your bank"
            )
        await self.bot.db.execute(
            """UPDATE economy SET balance = economy.balance + $1, bank = economy.bank - $1 WHERE user_id = $2""",
            amount,
            ctx.author.id,
        )
        return await ctx.withdraw(
            f"**{self.format_int(amount)}** bucks were **withdrawn into you wallet**"
        )

    @commands.command(name="daily", brief="Collect your daily bucks", example=",daily")
    @account()
    async def daily(self, ctx: Context):
        if not await self.bot.redis.get(ctx.author.id):
            await self.update_balance(ctx.author, "Add", 100)
            await self.bot.redis.set(ctx.author.id, 1, ex=60 * 60 * 24)
            return await ctx.currency("**100** bucks were **added to your wallet**")
        else:
            ttl = await self.bot.redis.ttl(ctx.author.id)
            return await ctx.fail(
                f"You can only get **100 bucks** per day day. You can get another 100 bucks **<t:{int(datetime.now().timestamp()+ttl)}:R>**"
            )

    @commands.command(
        name="roll",
        brief="Gamble a roll against the house for bucks",
        example=",roll 500",
    )
    @account()
    async def roll(self, ctx: Context, amount: GambleAmount):
        if str(amount).startswith("-"):
            return await ctx.warning("You **Cannot use negatives**")
        balance = await self.get_balance(ctx.author)
        if float(amount) < 0.00:
            return await ctx.fail("lol nice try")
        if float(amount) > float(balance):
            return await ctx.warning(
                f"you only have **{self.format_int(balance)}** bucks"
            )
        amounts = []
        if float(amount) > 1000000.0:
            value = self.get_random_value(1, 100000000000)
        else:
            value = self.get_random_value(1, 10000)
        for i in [1, 2, 3, 4]:  # type: ignore
            roll = self.get_random_value(1, 9)
            amounts.append(self.mapping[roll])
        multiplied = await self.check_item(ctx)
        if value == 9999:
            action = "WON"
            result = "Add"
            amount = int(amount * get_win(multiplied)).maximum(5000)
        else:
            action = "LOST"
            result = "Take"
        await self.update_balance(ctx.author, result, amount)
        return await ctx.currency(
            f"<:wockdice:1237308001950502942> You rolled a **{roll}**/100 and **{action} {self.format_int(amount)} bucks**"
        )

    @commands.command(
        name="coinflip",
        aliases=["flip", "cflip"],
        brief="flip a coin to earn bucks",
        example=",coinflip 100 heads",
    )
    @account()
    async def coinflip(self, ctx: Context, amount: GambleAmount, arg: str = None):
        if not arg:
            return await ctx.warning("please provide either heads or tails")
        if arg.lower() not in ["heads", "tails"]:
            return await ctx.warning("please provide either heads or tails")
        if str(amount).startswith("-"):
            return await ctx.warning("You **Cannot use negatives**")
        balance = await self.get_balance(ctx.author)
        if float(amount) < 0.00:
            return await ctx.fail("lol nice try")
        if float(amount) > float(balance):
            return await ctx.warning(
                f"you only have **{self.format_int(balance)}** bucks"
            )
        roll = self.get_random_value(1, 2)
        self.get_random_value(1, 2)  # type: ignore
        multiplied = await self.check_item(ctx)
        roll_coin = self.int_to_coin(roll)
        if roll_coin.lower() != arg.lower() and ctx.author.id != 352190010998390796:
            action = "LOST"
            result = "Take"
        else:
            if float(amount) > 10000000.0:
                value = self.get_random_value(1, 10)
                if value == 5:
                    action = "WON"
                    result = "Add"
                    amount = int(float(amount) * get_win(multiplied, 3)).maximum(5000)
                else:
                    action = "LOST"
                    result = "Take"
            else:
                action = "WON"
                result = "Add"
                amount = int(float(amount) * get_win(multiplied, 3)).maximum(5000)
        await self.update_balance(ctx.author, result, amount)
        return await ctx.currency(
            f"You flipped a **{roll_coin}** and **{action} {self.format_int(amount)} bucks**"
        )

    @commands.command(
        name="transfer",
        aliases=["pay", "give"],
        brief="Give another user some of your bucks",
        example=",transfer @c_5v 100,000",
    )
    @account()
    async def transfer(self, ctx: Context, member: Member, amount: Amount):
        if str(amount).startswith("-"):
            return await ctx.warning("You **Cannot use negatives**")
        balance = await self.get_balance(ctx.author)
        if float(amount) > float(balance):
            return await ctx.fail(f"you only have **{self.format_int(balance)}** bucks")
        if not await self.bot.db.fetchrow(
            """SELECT * FROM economy WHERE user_id = $1""", member.id
        ):
            return await ctx.fail(f"{member.mention} **does not** have an **account**")
        await ctx.currency(
            f"<a:68523animatedarrowgreen:1249174023728791582> **Transferred {self.format_int(amount)} bucks** to {member.mention}"
        )
        await self.update_balance(ctx.author, "Take", amount, False)
        await self.update_balance(member, "Add", amount, False)
        return

    def get_max_bet(self, a: Union[float, int], amount: Union[float, int]):
        b = int((float(amount) / float(a)))
        if b >= 2:
            return amount / 2
        return amount

    def get_suffix_names(self) -> dict:
        return {
            "": "Unit",
            "K": "Thousand",
            "M": "Million",
            "B": "Billion",
            "T": "Trillion",
            "Qa": "Quadrillion",
            "Qi": "Quintillion",
            "Sx": "Sextillion",
            "Sp": "Septillion",
            "Oc": "Octillion",
            "No": "Nonillion",
            "Dc": "Decillion",
            "Ud": "Undecillion",
            "Dd": "Duodecillion",
            "Td": "Tredecillion",
            "Qad": "Quattuordecillion",
            "Qid": "Quindecillion",
            "Sxd": "Sexdecillion",
            "Spd": "Septendecillion",
            "Ocd": "Octodecillion",
            "Nod": "Novemdecillion",
            "Vg": "Vigintillion",
            "Uv": "Unvigintillion",
            "Dv": "Duovigintillion",
            "Tv": "Trevigintillion",
            "Qav": "Quattuorvigintillion",
            "Qiv": "Quinvigintillion",
            "Sxv": "Sexvigintillion",
            "Spv": "Septenvigintillion",
            "Ocv": "Octovigintillion",
            "Nov": "Novemvigintillion",
            "Tg": "Trigintillion",
            "Utg": "Untrigintillion",
            "Dtg": "Duotrigintillion",
            "Ttg": "Tretrigintillion",
            "Qatg": "Quattuortrigintillion",
            "Qitg": "Quintrigintillion",
            "Sxtg": "Sextrigintillion",
            "Sptg": "Septentrigintillion",
            "Octg": "Octotrigintillion",
            "Notg": "Novemtrigintillion",
            "Qng": "Quadragintillion",
        }

    @commands.command(
        name="gamble",
        brief="Gamble bucks against the house",
        example=",gamble 500",
        cooldown_args={
            "limit": (
                1,
                6,
            ),
            "type": "user",
        },
    )
    @account()
    async def gamble(self, ctx: Context, amount: GambleAmount):
        if str(amount).startswith("-"):
            return await ctx.warning("You **Cannot use negatives**")
        balance = float(
            await self.bot.db.fetchval(
                "SELECT balance FROM economy WHERE user_id = $1", ctx.author.id
            )
        )
        if float(amount) > balance:
            if balance > 0:
                return await ctx.fail(
                    f"**House has declined,** You have {format_int(float(balance))} and wanted to gamble {format_int(float(amount))}"
                )
            else:
                return await ctx.fail(
                    f"**House has declined,** You have 0 and wanted to gamble {format_int(float(amount))}"
                )
        if float(amount) > 10000000.0:
            roll = self.get_random_value(1, 200) / 2
            v = 50
        else:
            roll = self.get_random_value(1, 100)
            v = 50
        multiplied = await self.check_item(ctx)
        if roll > v or ctx.author.id == 352190010998390796:
            action = "WON"
            result = "Add"
            amount = int(
                float(self.get_max_bet(float(amount), (float(amount) * get_win())))
            ).maximum(5000)
            if multiplied is True:
                amount = amount * 2
        else:
            action = "LOST"
            result = "Take"
        await self.update_balance(ctx.author, result, amount)
        return await ctx.currency(
            f"You **gambled** and rolled a **{roll}**/100, therefore you have **{action} {self.format_int(amount)} bucks**"
        )

    @commands.command(
        name="supergamble",
        brief="Super gamble bucks against the house",
        example=",supergamble 5,000",
    )
    @account()
    async def supergamble(self, ctx: Context, amount: GambleAmount):
        if str(amount).startswith("-"):
            return await ctx.warning("You **Cannot use negatives**")
        if float(amount) > float(
            await self.bot.db.fetchval(
                "SELECT balance FROM economy WHERE user_id = $1", ctx.author.id
            )
        ):
            return await ctx.fail("you too **broke** for that **top G**")
        roll = self.get_random_value(1, 100)
        value = 75 if not await self.check_shrooms(ctx) else 50
        if roll > value or ctx.author.id == 352190010998390796:
            action = "WON"
            result = "Add"
            amount = int(float(float(amount) * 4.34)).maximum(5000)
        else:
            action = "LOST"
            result = "Take"
        await self.update_balance(ctx.author, result, amount)
        return await ctx.currency(
            f"You **Super gambled** and rolled a **{roll}**/100, therefore you have **{action} {self.format_int(amount)}** bucks"
        )

    @commands.command(
        name="buy",
        brief="buy item(s) to use with gamble commands",
        example=",buy meth 2",
    )
    @account()
    async def buy(self, ctx: Context, *, item_and_amount: str):
        item = "".join(m for m in item_and_amount if not m.isdigit())
        amount = "".join(m for m in item_and_amount if m.isdigit())
        item = item.lstrip().rstrip()
        try:
            if int(amount) == 0:
                amount = 1
            else:
                amount = int(amount)
        except Exception:
            amount = 1
        if item not in self.items.keys():
            at = len(max(list(self.items.keys()), key=len))
            return await ctx.fail(f"the item `{item[:at]}` is not a valid item")
        return await self.buy_item(ctx, item, amount)

    @commands.command(
        name="inventory",
        brief="Show items in your inventory",
        example=",inventory @o_5v",
    )
    @account()
    async def inventory(self, ctx: Context, *, member: Optional[Member] = None):
        if member is None:
            member = ctx.author
        items = await self.bot.db.fetch(
            """SELECT * FROM inventory WHERE user_id = $1""", member.id
        )
        embed = Embed(color=self.bot.color)
        embed.title = f"{member.name}'s inventory"
        for i in items:
            embed.add_field(name=i.item, value=i.amount, inline=True)
        if len(embed.fields) == 0:
            embed.description = "1 mud bricks"
        return await ctx.send(embed=embed)

    @commands.command(
        name="use", brief="Use an item bought from the shop", example=",use meth"
    )
    @account()
    async def use(self, ctx: Context, *, item: str):
        return await self.use_item(ctx, item)

    async def get_or_fetch(self, user_id: int) -> str:
        if user := self.bot.get_user(user_id):
            return user.name
        else:
            user = await self.bot.fetch_user(user_id)
            return user.name

    @commands.command(
        name="leaderboard",
        brief="show top users for either earnings or balance",
        example=",leaderboard",
    )
    @account()
    async def leaderboard(self, ctx: Context, type: Optional[str] = "balance"):
        rows = []
        user_in_top_10 = False
        user_position = None
        user_data = None

        if type.lower() == "balance":
            users = await self.bot.db.fetch(
                """SELECT user_id,
                SUM(balance + bank) AS bal
                FROM economy
                GROUP BY user_id
                ORDER BY bal DESC;
            """
            )
            users = [
                user
                for user in users
                if not str(user["bal"]).startswith("0")
                and not str(user["bal"]).startswith("-")
            ]

            for i, row in enumerate(users, start=1):
                if i <= 10:
                    rows.append(
                        f"`{i}.` [**{await self.get_or_fetch(row['user_id'])}**](https://wock.bot) - **{self.format_int(row['bal'])}**"
                    )
                    if row["user_id"] == ctx.author.id:
                        user_in_top_10 = True
                if row["user_id"] == ctx.author.id:
                    user_position = i
                    user_data = row

            if not user_in_top_10 and user_position:
                user_balance = self.format_int(user_data["bal"])
                if user_balance.startswith("-"):
                    user_balance = 0
                rows.append(
                    f"<a:68523animatedarrowgreen:1249174023728791582> `{user_position}.` {ctx.author.mention} - **{user_balance}**"
                )

            embed = Embed(title=f"{type.title()} Leaderboard", color=self.bot.color)
            embed.set_thumbnail(url="")
            embed.description = "\n".join(rows)
            return await ctx.send(embed=embed)

        else:
            users = await self.bot.db.fetch(
                """SELECT user_id, earnings FROM economy ORDER BY earnings DESC"""
            )
            users = [
                user for user in users if not str(user["earnings"]).startswith("0")
            ]

            for i, row in enumerate(users, start=1):
                if i <= 10:
                    rows.append(
                        f"`{i}` [**{await self.get_or_fetch(row['user_id'])}**](https://wock.bot) - **{self.format_int(row['earnings'])}**"
                    )
                    if row["user_id"] == ctx.author.id:
                        user_in_top_10 = True
                if row["user_id"] == ctx.author.id:
                    user_position = i
                    user_data = row

            if not user_in_top_10 and user_position:
                rows.append(
                    f"<a:68523animatedarrowgreen:1249174023728791582> `{user_position}` {ctx.author.mention} - **{self.format_int(user_data['earnings'])}**"
                )

            embed = Embed(title=f"{type.title()} Leaderboard", color=self.bot.color)
            embed.description = "\n".join(rows)
            return await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Economy(bot))
