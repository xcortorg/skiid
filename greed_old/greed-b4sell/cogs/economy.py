from builtins import int, isinstance, str
import discord
from discord.ext import commands, tasks
from discord.ext.commands import Context, CommandError, check
from discord import Member as DiscordMember, Embed, ui
import random
import asyncio
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import matplotlib.pyplot as plt
import numpy as np
import io
import matplotlib.pyplot as plt
from io import BytesIO
from io import BytesIO
import base64
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib
from PIL import Image, ImageDraw, ImageMath
from typing import Union, Optional
from discord.ui import Button, View
from discord import Embed
from tool.important.subclasses.command import Member, User
from tool.important.subclasses.color import ColorConverter
from tool.chart import EconomyCharts
from discord.utils import format_dt
from collections import defaultdict
import random
import asyncio
from datetime import datetime, timedelta
from dataclasses import dataclass
from pytz import timezone
from tools import thread
from loguru import logger
from tool.emotes import EMOJIS
from discord import Embed, ui, Interaction
from discord import ui, Embed, ButtonStyle
from tool.greed import Greed
import time

log = logger
MAX_GAMBLE = 250_000
BOOSTER_ROLE_ID = 1301664266868363356
GUILD_ID = 1301617147964821524


class OverMaximum(CommandError):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


class GambleConverter(commands.Converter):
    async def convert(self, ctx: Context, argument: str) -> float:
        try:
            amount = float(argument.replace(",", ""))
            if amount <= 0:
                raise ValueError("Amount must be positive")
            if amount > MAX_GAMBLE:
                raise OverMaximum(f"Maximum gamble amount is {MAX_GAMBLE:,}")

            balance = await ctx.bot.db.fetchval(
                "SELECT balance FROM economy WHERE user_id = $1", ctx.author.id
            )
            if amount > balance:
                raise ValueError(f"You only have {balance:,} bucks")
            return amount
        except ValueError as e:
            raise CommandError(str(e))


def format_large_number(num: Union[int, float]) -> str:
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
    num_str = str(num)
    if "." in num_str:
        num_str = num_str[: num_str.index(".")]
    num_len = len(num_str)
    if num_len <= 3:
        return num_str
    suffix_index = (num_len - 1) // 3
    if suffix_index >= len(suffixes):
        return f"{num} is too large to format."
    scaled_num = int(num_str[: num_len - suffix_index * 3])
    return f"{scaled_num}{suffixes[suffix_index]}"


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


class BlackjackView(ui.View):
    def __init__(self, ctx, bot):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.bot = bot
        self.move = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user == self.ctx.author

    @ui.button(label="Hit", style=discord.ButtonStyle.green)
    async def hit_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        self.move = 0
        self.stop()

    @ui.button(label="Stay", style=discord.ButtonStyle.gray)
    async def stay_button(self, interaction: discord.Interaction, button: ui.Button):
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
            return random.uniform(4.5, 7.5)
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


def ensure_non_negative(value: float) -> float:
    return max(value, 0)


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


def parse_shorthand_amount(amount_str: str) -> float:
    """
    Parse a string with shorthand notation like 100k, 5m, etc. into a float.
    Supports k (thousand), m (million), b (billion), t (trillion).
    """
    amount_str = amount_str.replace(",", "").strip().lower()

    # Define multipliers for suffixes
    multipliers = {
        "k": 1_000,
        "m": 1_000_000,
        "b": 1_000_000_000,
        "t": 1_000_000_000_000,
    }

    # Check for shorthand notation
    for suffix, multiplier in multipliers.items():
        if amount_str.endswith(suffix):
            try:
                # Extract the number part and multiply by the appropriate factor
                number_part = amount_str[: -len(suffix)]
                return float(number_part) * multiplier
            except ValueError:
                # If conversion fails, return None to handle the error in the converter
                return None

    # If no suffix found, try to convert directly to float
    try:
        return float(amount_str)
    except ValueError:
        return None


class BankAmount(commands.Converter):
    name = "BankAmount"

    async def convert(self, ctx: Context, argument: Union[int, float, str]):
        if isinstance(argument, str):
            argument = argument.replace(",", "").strip().lower()

            # Get bank balance
            bank_balance = (
                await ctx.bot.db.fetchval(
                    "SELECT bank FROM economy WHERE user_id = $1", ctx.author.id
                )
                or 0.0
            )

            # Handle special keywords
            if argument == "all":
                argument = bank_balance
            elif argument == "half":
                argument = bank_balance / 2
            elif argument == "quarter":
                argument = bank_balance / 4
            else:
                # Handle shorthand notation
                parsed_amount = parse_shorthand_amount(argument)
                if parsed_amount is not None:
                    argument = parsed_amount
                else:
                    try:
                        argument = float(argument)
                    except Exception:
                        await ctx.warning("Please provide a valid **Amount**")
                        raise OverMaximum("lol")  # MissingRequiredArgument(BankAmount)

        # Convert to float for consistency
        argument = float(argument)

        # Check balance
        balance = (
            await ctx.bot.db.fetchval(
                "SELECT bank FROM economy WHERE user_id = $1", ctx.author.id
            )
            or 0.0
        )

        if argument > balance:
            raise commands.CommandError(
                f"You only have **{format_int(balance)}** bucks in your bank"
            )
        if argument < 0:
            raise commands.CommandError("you can't withdraw an amount below 0")

        return argument


class Amount(commands.Converter):
    name = "Amount"

    async def convert(self, ctx: Context, argument: Union[int, float, str]):
        if isinstance(argument, str):
            argument = argument.replace(",", "").strip().lower()

            # Get wallet balance
            wallet_balance = (
                await ctx.bot.db.fetchval(
                    "SELECT balance FROM economy WHERE user_id = $1", ctx.author.id
                )
                or 0.0
            )

            # Handle special keywords
            if argument == "all":
                argument = wallet_balance
            elif argument == "half":
                argument = wallet_balance / 2
            elif argument == "quarter":
                argument = wallet_balance / 4
            else:
                # Handle shorthand notation
                parsed_amount = parse_shorthand_amount(argument)
                if parsed_amount is not None:
                    argument = parsed_amount
                else:
                    try:
                        argument = float(argument)
                    except Exception:
                        await ctx.warning("Please provide a valid **Amount**")
                        raise OverMaximum("lol")  # MissingRequiredArgument(Amount)

        # Convert to float for consistency
        argument = float(argument)

        # Check balance
        balance = (
            await ctx.bot.db.fetchval(
                "SELECT balance FROM economy WHERE user_id = $1", ctx.author.id
            )
            or 0.0
        )

        if argument > balance:
            raise commands.CommandError(
                f"You only have **{format_int(balance)}** bucks"
            )
        if argument <= 0:
            raise commands.CommandError("you can't use an amount below 0")

        return argument


class GambleAmount(commands.Converter):
    name = "GambleAmount"

    async def convert(self, ctx: Context, argument: Union[int, float, str]):
        balance = float(
            await ctx.bot.db.fetchval(
                "SELECT balance FROM economy WHERE user_id = $1", ctx.author.id
            )
            or 0.0
        )

        if isinstance(argument, str):
            argument = argument.replace(",", "").strip().lower()

            if argument == "all":
                amount = balance
            elif argument == "half":
                amount = balance / 2
            elif argument == "quarter":
                amount = balance / 4
            else:
                # Handle shorthand notation
                parsed_amount = parse_shorthand_amount(argument)
                if parsed_amount is not None:
                    amount = parsed_amount
                else:
                    try:
                        amount = float(argument)
                    except ValueError:
                        raise CommandError(
                            f"Invalid amount: '{argument}' is not a valid number"
                        )
        else:
            amount = float(argument)

        # Ensure amount is positive
        if amount <= 0:
            raise CommandError("Amount must be positive")

        # Cap at maximum allowed gamble amount (convert to float)
        if amount >= float(MAX_GAMBLE):
            amount = float(MAX_GAMBLE)

        # Ensure amount doesn't exceed user's balance
        if amount > balance:
            amount = balance

        # Final check for valid amount
        if amount <= 0:
            raise CommandError("Insufficient funds")

        return amount


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


matplotlib.use("agg")

EMOJIS["diamond"] = "💎"


class Economy(commands.Cog):
    def __init__(self, bot: Greed):
        self.bot = bot
        self.winner = None
        self.first_wealthy_user = None  # Track the first user to hit 10 million
        self.check_interval = 60  # Check the leaderboard every 60 seconds

        # Start the periodic leaderboard check
        self.bot.loop.create_task(self.check_leaderboard())
        self.locks = {}
        self.earnings_task.start()
        self.last_reset = datetime.now().timestamp()
        self.donator_wins = {}
        self.reacted_users = []
        self.locks = defaultdict(asyncio.Lock)
        self.default_emojis = [
            "<:4695whiteup:1328326087108726855>",
            "<:7373whitedown:1328326088480522332>",
            "<:2052whiteleft:1328326086211407995>",
            "<:9847whiteright:1328326090359570434>",
        ]  # Fixed emojis for DDR
        self.emoji_to_text = {  # Map emojis to their text representation
            "<:4695whiteup:1328326087108726855>": "up",
            "<:7373whitedown:1328326088480522332>": "down",
            "<:2052whiteleft:1328326086211407995>": "left",
            "<:9847whiteright:1328326090359570434>": "right",
        }
        self.active_combos = {}
        self.active_ctx = {}
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
                "emoji": EMOJIS["devilnigga"],
            },
            "white powder": {
                "price": 500000,
                "description": "allows you to win double from a coinflip for 1 minute",
                "duration": 60,
                "emoji": EMOJIS["pwder"],
            },
            "oxy": {
                "price": 400000,
                "description": "allows you 2x more bucks when you win a gamble for 30 seconds",
                "duration": 30,
                "emoji": EMOJIS["oxy"],
            },
            "meth": {
                "description": "roll 2x more for 4 minutes",
                "price": 350000,
                "duration": 240,
                "emoji": EMOJIS["mth"],
            },
            "shrooms": {
                "description": "increases your chances of winning gamble commands by 10% for 10 minutes",
                "price": 100000,
                "duration": 600,
                "emoji": EMOJIS["shrrom"],
            },
        }
        self.symbols = ["♠", "♥", "♦", "♣"]

        self.achievements = {
            "Lets begin.": {
                "description": f"open an account through {self.bot.user.name} for gambling",
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
        self.clear_items.start()  # Start the clear_items task when the cog is loaded

    async def get_lab(self, user_id):
        """Fetch user's lab details."""
        return await self.bot.db.fetchrow(
            "SELECT * FROM labs WHERE user_id = $1", user_id
        )

    async def update_lab(self, user_id, **kwargs):
        """Update lab data."""
        query = (
            "UPDATE labs SET "
            + ", ".join(f"{k} = ${i+1}" for i, k in enumerate(kwargs.keys()))
            + " WHERE user_id = ${}".format(len(kwargs) + 1)
        )
        await self.bot.db.execute(query, *kwargs.values(), user_id)

    @tasks.loop(minutes=1)  # Task runs every 60 minutes
    async def earnings_task(self):
        """Task to add earnings every minute for users with labs."""
        try:
            # Fetch all labs
            labs = await self.bot.db.fetch("SELECT * FROM labs")

            for lab in labs:
                user_id = lab["user_id"]
                ampoules = lab["ampoules"]
                earnings_per_hour = ampoules * 3_276
                earnings_per_minute = (
                    earnings_per_hour / 60
                )  # Convert to earnings per minute

                # Fetch the user's storage limit and current earnings
                user_lab = await self.bot.db.fetchrow(
                    "SELECT earnings, storage FROM labs WHERE user_id = $1", user_id
                )

                if not user_lab:
                    continue  # Skip if no lab data found for the user

                current_earnings = user_lab["earnings"]
                storage_limit = user_lab["storage"]  # Storage limit from the labs table

                # Ensure earnings do not exceed the storage limit
                new_earnings = current_earnings + earnings_per_minute
                if new_earnings > storage_limit:
                    new_earnings = storage_limit  # Cap earnings to storage limit

                # Update the user's earnings in the labs table
                await self.bot.db.execute(
                    "UPDATE labs SET earnings = $1 WHERE user_id = $2",
                    new_earnings,  # Set the updated earnings (with the cap applied)
                    user_id,
                )

        except Exception as e:
            print(f"Error occurred in earnings_task: {e}")

    @commands.Cog.listener()
    async def on_ready(self):
        """Ensure the earnings task is running when the cog is loaded."""
        if not self.earnings_task.is_running():
            self.earnings_task.start()

    def cog_unload(self):
        """Stop the earnings task when the cog is unloaded."""
        if self.earnings_task.is_running():
            self.earnings_task.stop()

    def generate_pie_chart(
        self, member_name: str, progress: float, avatar_b64: str
    ) -> BytesIO:
        """
        Generates and updates the pie chart with progress.
        The chart starts off grey and gets filled with green as the user answers questions correctly.
        """
        # We want to represent progress as a portion of the pie
        data = [progress, 1 - progress]  # The progress and the remaining part
        colors = ["#7BB662", "#7B7B7B"]  # Grey for remaining, green for progress
        labels = [f"{int(progress * 100)}%", "Locked"]
        # 7BB662
        # Decode avatar from base64
        avatar_bytes = base64.b64decode(avatar_b64)
        avatar_image = Image.open(BytesIO(avatar_bytes)).convert("RGBA")

        # Create circular mask for the avatar
        mask = Image.new("L", avatar_image.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + avatar_image.size, fill=255)
        alpha = ImageMath.eval("a*b/255", a=avatar_image.split()[3], b=mask).convert(
            "L"
        )
        avatar_image.putalpha(alpha)

        # Generate pie chart
        plt.figure(figsize=(6, 8))
        wedges, _ = plt.pie(
            data, colors=colors, startangle=90, wedgeprops=dict(width=0.3)
        )
        plt.axis("equal")

        # Overlay the avatar image onto the chart
        width, height = avatar_image.size
        aspect_ratio = height / width
        half_width = 0.91
        half_height = aspect_ratio * half_width
        extent = [-half_width, half_width, -half_height, half_height]
        plt.imshow(avatar_image, extent=extent, zorder=-1)

        # Add a legend
        plt.legend(
            wedges,
            labels,
            title=f"{member_name}'s Safe",
            loc="upper center",
            bbox_to_anchor=(0.5, 0.08),
            facecolor="#2C2F33",
            edgecolor="#23272A",
        )

        # Save chart to memory (in a buffer)
        buffer = BytesIO()
        plt.savefig(buffer, format="png", transparent=True)
        plt.close()

        buffer.seek(0)  # Reset the pointer to the start of the buffer
        return buffer

    def cog_unload(self):
        """Stop tasks when the cog is unloaded."""
        self.clear_items.cancel()
        self.investment_update_task.cancel()

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

    @thread
    def generate_cards(self):
        cards_out = list()
        cards_out_n = list()
        amount = 0
        _c = {
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
        cards = [card for card in _c]
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

    def format_int(self, n: Union[float, str, int]) -> str:
        try:
            if isinstance(n, str):
                n = float(n.replace(",", ""))
            if isinstance(n, float):
                formatted = f"{n:,.2f}"
            else:
                formatted = f"{n:,}"
            if float(n) < 0:
                return f":clown: ${formatted}"
            return f"${formatted}"
        except ValueError:
            return "Invalid number"

    async def get_balance(
        self, member: DiscordMember, with_bank: bool = False
    ) -> Union[float, tuple[float, float]]:
        if with_bank:
            data = await self.bot.db.fetchrow(
                "SELECT balance, bank FROM economy WHERE user_id = $1", member.id
            )
            if not data:
                return 0.0, 0.0
            balance = data["balance"] or 0.0
            bank = data["bank"] or 0.0
            return float(balance), float(bank)
        else:
            balance = await self.bot.db.fetchval(
                "SELECT balance FROM economy WHERE user_id = $1", member.id
            )
            return float(balance) if balance else 0.0

    def get_expiration(self, item: str) -> tuple:
        now = datetime.now()
        ex = now + timedelta(seconds=self.items[item].duration)
        return now, ex

    async def use_item(self, ctx: Context, item: str):
        await self.check_item(ctx, ctx.author)
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

    def get_random_amount(self, difficulty: str):
        if difficulty == "easy":
            return random.randint(1000, 6000)
        elif difficulty == "medium":
            return random.randint(10000, 25000)
        elif difficulty == "hard":
            return random.randint(30000, 60000)
        else:
            return 0

    def generate_easy_question(self):
        a = random.randint(1, 30)
        b = random.randint(4, 40)
        question = f"-# What is {a} + {b}?"
        answer = a + b
        return question, answer

    def generate_medium_question(self):
        a = random.randint(10, 150)
        b = random.randint(10, 170)
        question = f"-# What is {a} + {b}?"
        answer = a + b
        return question, answer

    def generate_hard_question(self):
        a = random.randint(1, 1000)
        b = random.randint(1, 2000)
        question = f"-# What is {a} * {b}?"
        answer = a * b
        return question, answer

    async def buy_item(self, ctx: Context, item: str, amount: int = 1):
        if amount > 99:
            return await ctx.fail("you can only buy 99")
        if item not in self.items.keys():
            return await ctx.fail("not a valid item")
        price = self.items[item].price * amount
        balance = await self.get_balance(ctx.author)
        if float(price) > float(balance):
            return await ctx.fail("you do not have enough for that")
        await self.bot.db.execute(
            """INSERT INTO inventory (user_id, item, amount) VALUES($1, $2, $3) ON CONFLICT (user_id, item) DO UPDATE SET amount = inventory.amount + excluded.amount""",
            ctx.author.id,
            item,
            amount,
        )
        await self.update_balance(ctx.author, "Take", price, False)
        return await ctx.success(
            f"**Purchased** `{amount}` **{item}** for `{self.items[item].price*amount}`"
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

    @tasks.loop(minutes=1)
    async def clear_items(self):
        """Remove expired items from the `used_items` table."""
        try:
            # Batch delete expired items
            await self.bot.db.execute(
                """DELETE FROM used_items WHERE expiration <= $1""", datetime.now()
            )
        except Exception as e:
            # Log errors if any occur
            self.bot.logger.error(f"Error clearing expired items: {e}")

    async def check_item(
        self, ctx: Context, member: Optional[discord.Member] = None
    ) -> bool:
        """Check if a member has a valid item."""
        cn = ctx.command.qualified_name
        item = None

        if member is None:
            member = ctx.author

        # Map commands to items
        command_to_item = {
            "coinflip": "white powder",
            "steal": "purple devil",
            "gamble": "oxy",
            "roll": "meth",
            "scratch": "ticket",
        }
        item = command_to_item.get(cn)

        if not item:
            return False

        # Fetch expiration for the given item and member
        kwargs = [member.id, item]
        data = await self.bot.db.fetchrow(
            """SELECT expiration FROM used_items WHERE user_id = $1 AND item = $2""",
            *kwargs,
        )
        if not data:
            return False

        # Check expiration time
        if data["expiration"].timestamp() <= datetime.now().timestamp():
            await self.bot.db.execute(
                """DELETE FROM used_items WHERE user_id = $1 AND item = $2""", *kwargs
            )
            return False

        return True

    @clear_items.before_loop
    async def before_clear_items(self):
        """Ensure the bot is ready before starting the loop."""
        await self.bot.wait_until_ready()

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
                """UPDATE economy SET balance = GREATEST(economy.balance - $1, 0), earnings = economy.earnings - $2, total = economy.total + $4 WHERE user_id = $3 RETURNING balance""",
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

    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignore messages from bots
        if message.author.bot:
            return

        # Check if there's an active combo for the channel
        combo = self.active_combos.get(message.channel.id)
        if not combo:
            return

        # Normalize the user's message
        user_input = message.content.lower().strip().split()
        normalized_input = " ".join(self.emoji_to_text.get(e, e) for e in user_input)

        # Normalize the combo
        normalized_combo = " ".join(self.emoji_to_text[e] for e in combo.split())

        # Check if the normalized user input matches the normalized combo
        if normalized_input == normalized_combo:
            # Remove the active combo since we have a winner
            del self.active_combos[message.channel.id]

            # Get the ctx for the current channel
            ctx = self.active_ctx.get(message.channel.id)
            if not ctx:
                return  # If ctx doesn't exist, return early

            # Generate a random payout
            amount = random.randint(1000, 5000)

            # Debugging: Show match success
            logger.info(
                f"[DEBUG] Combo matched by {message.author} in channel {message.channel.id}"
            )

            # Update the winner's balance in the database
            await self.bot.db.execute(
                """UPDATE economy SET balance = balance + $1, earnings = earnings + $1 WHERE user_id = $2""",
                amount,
                message.author.id,
            )

            # Use ctx.currency() to announce the win and payout message
            return await ctx.currency(
                f"**{message.author.mention}**, you typed the correct combo and won the DDR minigame, earning **`{amount}` bucks!**"
            )

    @commands.command(
        name="blackjack",
        aliases=["bj"],
        brief="play blackjack against the house to gamble bucks",
        example=",blackjack 100",
    )
    @account()
    @commands.cooldown(1, 10, commands.BucketType.user)
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
            win_amount = float(amount) * 2  # Changed to 2x the bet amount

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
            thumbnail_url = "https://media.discordapp.net/attachments/1201966711826555002/1250569957830295704/poker_cards.png?format=webp&quality=lossless"
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
                        bot_stay = random.randint(0, 1) == 0

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
                        em.description = (
                            f"you won **{self.format_int(int(win_amount))}** bucks"
                        )
                        await self.update_balance(ctx.author, "Add", int(win_amount))
                    else:
                        em.description = (
                            f"you lost **{self.format_int(float(amount))}** bucks"
                        )
                        await self.update_balance(ctx.author, "Take", amount)

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
                            em.description = f"I went over 21 and you won **{self.format_int(int(win_amount))} bucks**"
                            await self.update_balance(
                                ctx.author, "Add", int(win_amount)
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
                        em.set_thumbnail(url=thumbnail_url)
                        await msg.edit(embed=em, view=None)
                        return
                except Exception:
                    pass

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
                em.set_thumbnail(url=thumbnail_url)
                await msg.edit(embed=em, view=view)

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
                    em.description = f"I went over 21 and you won **{self.format_int(int(win_amount))} bucks**"
                    await self.update_balance(ctx.author, "Add", int(win_amount))

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

    @commands.command(
        name="balance",
        aliases=["earnings", "bal", "wallet"],
        brief="Show your wallet, bank, lab earnings, and rank on the leaderboard",
        example=",balance",
    )
    @commands.cooldown(2, 10, commands.BucketType.guild)
    async def balance(self, ctx: commands.Context, member: discord.Member = None):
        """Shows the user's balance, bank, lab earnings, and rank."""
        member = member or ctx.author

        # Fetch user's balance and bank
        user_data = await self.bot.db.fetchrow(
            "SELECT balance, bank FROM economy WHERE user_id = $1", member.id
        )

        if not user_data:
            return await ctx.fail(f"**{member.name}** doesn't have an account.")

        balance = user_data["balance"]
        bank = user_data["bank"]

        # Fetch user's lab earnings if they own a lab
        lab_data = await self.bot.db.fetchrow(
            "SELECT earnings FROM labs WHERE user_id = $1", member.id
        )
        lab_earnings = lab_data["earnings"] if lab_data else 0  # Default to 0 if no lab

        # Fetch leaderboard rankings
        leaderboard_query = """
            SELECT user_id, SUM(balance + bank) AS total
            FROM economy
            GROUP BY user_id
            ORDER BY total DESC
        """
        users = await self.bot.db.fetch(leaderboard_query)

        # Determine user's rank
        rank = next(
            (idx + 1 for idx, user in enumerate(users) if user["user_id"] == member.id),
            "Unranked",
        )

        # Create embed response
        embed = discord.Embed(color=self.bot.color)
        embed.set_author(
            name=f"{member.name}'s Balance", icon_url=member.display_avatar.url
        )
        embed.add_field(
            name="💰 Cash", value=f"{format_large_number(balance)} ", inline=True
        )
        embed.add_field(
            name="🏦 Bank", value=f"{format_large_number(bank)} ", inline=True
        )
        embed.add_field(
            name="<:ampoule:1337841915177205875> Lab Earnings",
            value=f"{format_large_number(lab_earnings)}",
            inline=False,
        )
        embed.set_footer(text=f"🏆 Rank: {rank}")

        await ctx.send(embed=embed)

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
            return await ctx.fail("**You already have an account**")

    @commands.command(
        name="deposit",
        aliases=["dep"],
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
            f"**{self.format_int(amount)}** bucks was **deposited into your bank**"
        )

    @commands.command(
        name="withdraw",
        brief="Withdraw bucks from your bank to your wallet",
        example=",withdraw 200",
    )
    @account()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def withdraw(self, ctx: Context, amount: BankAmount):
        if str(amount).startswith("-"):
            return await ctx.warning("You **Cannot use negatives**")
        balance, bank = await self.get_balance(ctx.author, with_bank=True)
        if float(amount) > bank:
            return await ctx.warning(
                f"You only have **{self.format_int(bank)}** bucks in your bank"
            )
        await self.bot.db.execute(
            """UPDATE economy SET balance = balance + $1, bank = bank - $1 WHERE user_id = $2""",
            amount,
            ctx.author.id,
        )
        return await ctx.withdraw(
            f"**{self.format_int(amount)}** bucks was **withdrawn from your bank**"
        )

    @commands.command(name="daily", brief="Collect your daily bucks", example=",daily")
    @account()
    async def daily(self, ctx: Context):
        if not await self.bot.redis.get(ctx.author.id):
            await self.update_balance(ctx.author, "Add", 1000)
            await self.bot.redis.set(ctx.author.id, 1, ex=60 * 60 * 24)
            return await ctx.currency("**1000** bucks was **added to your wallet**")
        else:
            ttl = await self.bot.redis.ttl(ctx.author.id)
            return await ctx.fail(
                f"You can only get **1000 bucks** per day day. You can get another 1000 bucks **<t:{int(datetime.now().timestamp()+ttl)}:R>**"
            )

    @commands.command(
        name="coinflip",
        aliases=["flip", "cflip", "cf"],
        brief="Flip a coin to earn bucks",
        example=",coinflip 100 heads",
    )
    @account()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def coinflip(self, ctx: Context, amount: GambleAmount, choice: str = None):
        try:
            if ctx.author.id not in self.locks:
                self.locks[ctx.author.id] = asyncio.Lock()

            async with self.locks[ctx.author.id]:
                if not choice or choice.lower() not in ["heads", "tails"]:
                    return await ctx.warning(
                        "Please provide either **heads** or **tails**."
                    )

                balance = await self.get_balance(ctx.author)
                if float(amount) > float(balance):
                    return await ctx.warning(
                        f"You only have **{self.format_int(balance)}** bucks."
                    )

                # Initial embed before flipping
                initial_embed = discord.Embed(
                    description="<a:coinspin:1337492774479724668> Flipping the coin...",
                    color=self.bot.color,
                )
                initial_embed.set_author(
                    name=ctx.author.display_name, icon_url=ctx.author.avatar.url
                )

                msg = await ctx.send(embed=initial_embed)

                # Simulate delay
                await asyncio.sleep(1.8)

                # Determine win or loss (40% chance of winning)
                roll_coin = random.choice(["Heads", "Tails"])
                won = random.random() < 0.4  # 40% win chance

                # Create result embed
                result_embed = discord.Embed(color=0x2A8000 if won else 0xFF0000)
                result_embed.set_author(
                    name="Coinflip Result", icon_url=ctx.author.avatar.url
                )

                if won:
                    win_amount = int(
                        float(amount) * get_win(await self.check_item(ctx), 3)
                    )
                    await self.update_balance(ctx.author, "Add", win_amount)
                    result_embed.add_field(
                        name="",
                        value=f"<:coin2:1337494740014202921> You flipped **{roll_coin}** and **WON** **{self.format_int(win_amount)}** 💵!",
                        inline=False,
                    )

                else:
                    await self.update_balance(ctx.author, "Take", amount)
                    result_embed.add_field(
                        name="",
                        value=f"<:startoken2:1337494741041942599> You flipped **{roll_coin}** and **LOST** **{self.format_int(amount)}** 💵.",
                        inline=False,
                    )

                # Edit initial message to show result
                await msg.edit(embed=result_embed)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(
                f"Error in coinflip command: {e}"
            )  # Using print instead of self.bot.logger.error
            await ctx.fail(
                "An error occurred while processing your coinflip. Please try again."
            )

    @commands.command(
        name="transfer",
        aliases=["pay", "give"],
        brief="Give another user some of your bucks",
        example=",transfer @sudosql 100000",
    )
    @account()  # assuming you have an account decorator
    async def transfer(self, ctx: Context, member: Member, amount: int):
        """Transfer bucks from one user to another."""

        # Ensure the amount is positive
        if amount <= 0:
            return await ctx.warning(
                "You **cannot** transfer a negative or zero amount."
            )

        # Get the sender's balance
        balance = await self.get_balance(ctx.author)

        # Check if the user has enough balance
        if amount > balance:
            return await ctx.fail(
                f"You only have **{self.format_int(balance)}** bucks."
            )

        # Ensure the recipient has an account
        if not await self.bot.db.fetchrow(
            """SELECT * FROM economy WHERE user_id = $1""", member.id
        ):
            return await ctx.fail(f"{member.mention} **does not** have an **account**.")

        # Perform the transaction
        await ctx.currency(
            f"<a:uparrow:1303882662225903718> **Transferred {self.format_int(amount)} bucks** to {member.mention}"
        )
        await self.update_balance(ctx.author, "Take", amount)
        await self.update_balance(member, "Add", amount)

    def format_int(self, amount: int) -> str:
        """Format the amount as a string with commas."""
        return "{:,}".format(amount)

    def get_max_bet(
        self, a: Union[float, int], amount: Union[float, int]
    ) -> Union[float, int]:
        """Get the max bet based on certain conditions."""
        b = int(amount / a)
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
        brief="Roll against the bot. If you roll higher, you win!",
        example=",gamble 500",
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def gamble(self, ctx: commands.Context, amount: GambleAmount):
        """User rolls a number against the bot. If the user rolls higher, they win."""

        if amount <= 0:
            return await ctx.fail("You must gamble a **positive** amount.")

        # Get user's balance
        balance = await self.bot.db.fetchval(
            "SELECT balance FROM economy WHERE user_id = $1", ctx.author.id
        )

        if balance is None or balance < amount:
            return await ctx.fail(
                f"You don't have enough bucks! Your balance is **{balance:,}**."
            )

        # Check if the user is a donator
        is_donator = await self.bot.db.fetchrow(
            """SELECT * FROM boosters WHERE user_id = $1""", ctx.author.id
        )

        # Roll numbers
        bot_roll = random.randint(1, 10)

        # Ensure you always roll higher if it's your user ID
        YOUR_USER_ID = 930383131863842816  # Replace with your actual Discord user ID
        if ctx.author.id == YOUR_USER_ID:
            user_roll = bot_roll + 1 if bot_roll < 10 else 10
        else:
            user_roll = random.randint(1, 10)

        # Determine multiplier: 1.5x for donators
        multiplier = 1.5 if is_donator else 1

        # Determine win/loss: user wins if they roll higher than the bot
        if user_roll > bot_roll:
            winnings = int(
                amount * 2 * multiplier
            )  # User wins with multiplier if they're a donator
            await self.bot.db.execute(
                "UPDATE economy SET balance = balance + $1 WHERE user_id = $2",
                winnings,
                ctx.author.id,
            )
            embed = discord.Embed(
                description=(
                    f"You have rolled **{user_roll}** and I have rolled **{bot_roll}**\n"
                    f"💰 You won **{winnings:,} bucks!**"
                ),
                color=0x2A8000,
            )
            if is_donator:
                embed.add_field(
                    name="Thank you for being a Booster!",
                    value="You're getting a **1.5x multiplier** for boosting [/greedbot](https://discord.gg/greedbot).",
                    inline=False,
                )
        else:
            await self.bot.db.execute(
                "UPDATE economy SET balance = balance - $1 WHERE user_id = $2",
                amount,
                ctx.author.id,
            )
            embed = discord.Embed(
                description=(
                    f"You have rolled **{user_roll}** and I have rolled **{bot_roll}**\n"
                    f"💰 You lost **{amount:,}** bucks!"
                ),
                color=0xFF0000,
            )

        await ctx.send(embed=embed)

    @commands.command(
        name="crash",
        brief="Play the crash game! Bet on how high the rocket can go before it crashes.",
        usage=",crash 500",
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def crash(self, ctx: commands.Context, amount: GambleAmount):
        """Play the crash game with realistic probabilities and anti-cheat measures."""
        if amount <= 0:
            return await ctx.fail("Bet amount must be positive!", delete_after=5)

        balance = await self.bot.db.fetchval(
            "UPDATE economy SET balance = balance - $1 "
            "WHERE user_id = $2 AND balance >= $1 RETURNING balance + $1",
            amount,
            ctx.author.id,
        )

        if not balance:
            return await ctx.fail("Insufficient funds!", delete_after=5)

        BASE_CRASH_CHANCE = 0.1
        MULTIPLIER_GROWTH = 0.56
        MAX_MULTIPLIER = 100.0
        UPDATE_INTERVAL = 3

        def calculate_crash_chance(current_multiplier):
            return min(0.95, BASE_CRASH_CHANCE + (current_multiplier**2.2) / 800)

        game_state = {
            "active": True,
            "multiplier": 1.0,
            "message": None,
            "last_update": ctx.message.created_at,
        }

        class CrashView(discord.ui.View):
            def __init__(self, bot):
                super().__init__(timeout=600)
                self.ctx = ctx
                self.bot = bot
                self.game_state = game_state

            @discord.ui.button(label="Cash Out", style=discord.ButtonStyle.green)
            async def cashout(
                self, interaction: discord.Interaction, button: discord.ui.Button
            ):
                await self.handle_action(interaction, "cashout")

            @discord.ui.button(label="Exit", style=discord.ButtonStyle.red)
            async def exit(
                self, interaction: discord.Interaction, button: discord.ui.Button
            ):
                await self.handle_action(interaction, "exit")

            async def handle_action(self, interaction, action_type):
                if interaction.user != ctx.author:
                    return await interaction.response.send_message(
                        "Hey u freak dont touch me..", ephemeral=True
                    )

                for item in self.children:
                    item.disabled = True

                await interaction.response.edit_message(view=self)
                self.game_state["active"] = False

                if action_type == "cashout":
                    final_multiplier = self.game_state["multiplier"]
                    winnings = int(amount * final_multiplier)
                    await self.bot.db.execute(
                        "UPDATE economy SET balance = balance + $1 WHERE user_id = $2",
                        winnings,
                        ctx.author.id,
                    )
                    profit = winnings - amount
                    embed = discord.Embed(
                        title="💰 Successful Cashout",
                        description=(
                            f"**Initial Bet:** {amount:,} 💵\n"
                            f"**Final Multiplier:** {final_multiplier:.2f}x\n"
                            f"**Total Winnings:** {winnings:,} 💵\n"
                            f"**Profit:** +{profit:,} 💵"
                        ),
                        color=0x2ECC71,
                    )
                else:
                    embed = discord.Embed(
                        title="🚪 Early Exit",
                        description=f"Exited at {self.game_state['multiplier']:.2f}x\n**-{amount:,}** 💵",
                        color=0xE74C3C,
                    )

                await self.game_state["message"].edit(embed=embed, view=self)
                self.stop()

            async def on_timeout(self):
                if self.game_state["active"]:
                    await self.bot.db.execute(
                        "UPDATE economy SET balance = balance + $1 WHERE user_id = $2",
                        amount,
                        ctx.author.id,
                    )
                    embed = discord.Embed(
                        title="⏰ Game Expired",
                        description="Game timed out - bet refunded!",
                        color=0xF1C40F,
                    )
                    await self.game_state["message"].edit(embed=embed, view=None)
                    self.game_state["active"] = False

        embed = discord.Embed(
            title="🚀 Crash Game Started",
            description=f"**Bet:** {amount:,} 💵\nCurrent Multiplier: 1.00x",
            color=self.bot.color,
        )
        view = CrashView(self.bot)
        view.game_state["message"] = await ctx.send(embed=embed, view=view)

        last_update = 0
        try:
            while game_state["active"] and game_state["multiplier"] < MAX_MULTIPLIER:
                await asyncio.sleep(1)

                current_time = time.time()
                if current_time - last_update >= UPDATE_INTERVAL:
                    last_update = current_time

                    crash_prob = calculate_crash_chance(game_state["multiplier"])
                    game_state["multiplier"] *= 1 + MULTIPLIER_GROWTH * random.uniform(
                        0.7, 1.3
                    )

                    if random.random() < crash_prob:
                        game_state["active"] = False
                        embed = discord.Embed(
                            title="💥 Rocket Crashed!",
                            description=(
                                f"Crashed at {game_state['multiplier']:.2f}x!\n"
                                f"**Initial Bet:** {amount:,} 💵\n"
                                f"**Lost:** -{amount:,} 💵"
                            ),
                            color=0xE74C3C,
                        )
                        await view.game_state["message"].edit(embed=embed, view=None)
                        break

                    potential_win = int(amount * game_state["multiplier"])
                    embed = discord.Embed(
                        title=f"🚀 Rocket is at {game_state['multiplier']:.2f}x",
                        description=(
                            f"**Initial Bet:** {amount:,} 💵\n"
                            f"**Current Value:** {potential_win:,} 💵\n"
                            f"**Next Update:** {UPDATE_INTERVAL}s"
                        ),
                        color=self.bot.color,
                    )
                    await view.game_state["message"].edit(embed=embed)

        except Exception as e:
            logger.error(f"Crash game error: {e}")
            await self.bot.db.execute(
                "UPDATE economy SET balance = balance + $1 WHERE user_id = $2",
                amount,
                ctx.author.id,
            )
            await view.game_state["message"].edit(
                content="⚠️ Game error - bet refunded!", embed=None, view=None
            )

    @commands.command(
        name="ladder",
        brief="Play the ladder game and climb multipliers!",
        example=",ladder 1000",
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def ladder(self, ctx: commands.Context, amount: GambleAmount):
        """Play a risk/reward ladder game with progressive difficulty."""
        if amount <= 0:
            return await ctx.fail("Bet must be positive!", delete_after=5)

        balance = await self.bot.db.fetchval(
            "SELECT balance FROM economy WHERE user_id = $1", ctx.author.id
        )
        if balance < amount:
            return await ctx.fail("Insufficient funds!", delete_after=5)

        await self.bot.db.execute(
            "UPDATE economy SET balance = balance - $1 WHERE user_id = $2",
            amount,
            ctx.author.id,
        )

        BASE_MULTIPLIERS = [1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 10.0]
        PROBABILITY_CURVE = [0.85, 0.70, 0.60, 0.50, 0.40, 0.30, 0.20, 0.10]
        INITIAL_STATE = {
            "current_step": 0,
            "collected": False,
            "crashed": False,
            "max_multiplier": random.choices(
                BASE_MULTIPLIERS, weights=PROBABILITY_CURVE
            )[0],
        }

        class LadderView(discord.ui.View):
            def __init__(self, bot):
                super().__init__(timeout=30)
                self.state = INITIAL_STATE
                self.bot = bot
                self.message = None
                self.embed = None

            def progress_bar(self):
                filled = "<:status_online:1302238596580773980>" * (
                    self.state["current_step"] + 1
                )
                empty = "<:status_offline:1302238593351421974>" * (
                    len(BASE_MULTIPLIERS) - self.state["current_step"] - 1
                )
                return filled + empty  # Fix for emoji rendering

            def current_multiplier(self):
                return (
                    BASE_MULTIPLIERS[self.state["current_step"]]
                    if not self.state["crashed"]
                    else 0
                )

            async def update_display(self, interaction=None):
                self.embed.clear_fields()
                self.embed.description = (
                    f"**Bet:** {amount:,} 💵\n"
                    f"**Current Multiplier:** {self.current_multiplier()}x\n"
                    f"**Max Potential:** {self.state['max_multiplier']}x"
                )
                self.embed.add_field(
                    name="Ladder Progress",
                    value=f"{self.progress_bar()}\n"
                    + "\n".join(
                        f"{'✅' if i <= self.state['current_step'] else '➖'} {multiplier}x"
                        for i, multiplier in enumerate(BASE_MULTIPLIERS)
                    ),
                )

                if interaction:
                    await interaction.response.edit_message(embed=self.embed, view=self)
                elif self.message:
                    await self.message.edit(embed=self.embed, view=self)
                else:
                    return self.embed

            @discord.ui.button(label="Climb", style=discord.ButtonStyle.green)
            async def climb(
                self, interaction: discord.Interaction, button: discord.ui.Button
            ):
                if interaction.user != ctx.author:
                    return await interaction.response.send_message(
                        "Nuh uh", ephemeral=True
                    )

                success_chance = PROBABILITY_CURVE[self.state["current_step"]]
                if random.random() > success_chance:
                    self.state["crashed"] = True
                    button.disabled = True
                    self.embed.color = 0xFF0000
                    self.embed.description = (
                        f"💥 Crashed at step {self.state['current_step']+1}!"
                    )
                    await self.end_game()
                    return

                self.state["current_step"] += 1

                if self.state["current_step"] >= len(BASE_MULTIPLIERS) - 1:
                    await self.collect(interaction)
                    return

                await self.update_display(interaction)

            @discord.ui.button(label="Collect", style=discord.ButtonStyle.blurple)
            async def collect(
                self, interaction: discord.Interaction, button: discord.ui.Button
            ):
                if interaction.user != ctx.author:
                    return await interaction.response.send_message(
                        "❌ Not your game!", ephemeral=True
                    )

                winnings = int(amount * self.current_multiplier())
                await self.bot.db.execute(
                    "UPDATE economy SET balance = balance + $1 WHERE user_id = $2",
                    winnings,
                    ctx.author.id,
                )

                self.state["collected"] = True
                self.embed.color = 0x00FF00
                self.embed.description = f"💰 Collected at {self.current_multiplier()}x!\n**+{winnings:,}** 💵"
                await self.end_game()
                await interaction.response.edit_message(embed=self.embed, view=self)

            async def end_game(self):
                for item in self.children:
                    item.disabled = True
                await self.message.edit(embed=self.embed, view=self)
                self.stop()

            async def on_timeout(self):
                if not self.state["collected"] and not self.state["crashed"]:
                    try:
                        refund = min(amount, 9223372036854775807)
                        await self.bot.db.execute(
                            "UPDATE economy SET balance = balance + $1 WHERE user_id = $2",
                            refund,
                            ctx.author.id,
                        )
                        self.embed.color = 0xFFFF00
                        self.embed.description = "⌛ Game timed out - bet refunded!"
                        await self.message.edit(embed=self.embed, view=None)
                    except Exception as e:
                        self.bot.logger.error(f"Error in ladder timeout: {e}")

        view = LadderView(self.bot)
        view.embed = discord.Embed(title="🏁 Ladder Game Started", color=self.bot.color)
        await view.update_display()
        view.message = await ctx.send(embed=view.embed, view=view)

    async def check_leaderboard(self):
        """Periodically check the leaderboard for the first person to reach 10 million."""
        while True:
            await asyncio.sleep(self.check_interval)

            # Query to fetch users' balance
            query = """
                SELECT user_id, SUM(balance + bank) AS balance FROM economy
                GROUP BY user_id
                ORDER BY balance DESC
            """
            users = await self.bot.db.fetch(query)

            if not users:
                continue

            # Check the first user to hit 10 million and mark them
            for user in users:
                balance = user["balance"]
                if balance >= 10000000 and self.first_wealthy_user is None:
                    self.first_wealthy_user = user["user_id"]
                    print(
                        f"User {user['user_id']} reached 10 million and is marked with a diamond emoji!"
                    )
                    break

    @commands.command(
        name="wealthy",
        brief="Show top users for either earnings or balance",
        example=",leaderboard",
        aliases=["wlb", "lb", "leaderboard"],
    )
    async def economy_leaderboard(self, ctx, type_: str = "balance"):
        """Command to display the leaderboard."""
        type_ = type_.lower()
        if type_ not in ["balance", "earnings"]:
            return await ctx.send("Invalid type! Choose `balance` or `earnings`.")

        query = (
            """
            SELECT user_id, SUM(balance + bank) AS balance FROM economy
            GROUP BY user_id
            ORDER BY balance DESC
        """
            if type_ == "balance"
            else """
            SELECT user_id, earnings AS balance FROM economy
            ORDER BY earnings DESC
        """
        )
        users = await self.bot.db.fetch(query)

        if not users:
            return await ctx.send("No users found in the leaderboard.")

        # Create chunks of 10 users each for pagination
        chunks = [users[i : i + 10] for i in range(0, len(users), 10)]
        embeds = []

        for page, chunk in enumerate(chunks, 1):
            rows = []
            for idx, user in enumerate(chunk, start=(page - 1) * 10 + 1):
                username = (
                    self.bot.get_user(user["user_id"]) or f"User {user['user_id']}"
                )
                balance = int(user["balance"])

                # Add diamond emoji only to the first person who hits 10 million
                diamond_emoji = (
                    EMOJIS["diamond"]
                    if self.first_wealthy_user == user["user_id"]
                    else ""
                )
                rows.append(
                    f"`{idx}.` **{username}** - **{format_large_number(balance)}**"
                )

            embed = Embed(
                title=f"{type_.title()} Global Leaderboard",
                description="\n".join(rows),
                color=self.bot.color,
            )
            embed.set_footer(text=f"Page {page}/{len(chunks)}")
            embeds.append(embed)

        await ctx.paginate(embeds)

    @commands.command(
        name="rob",
        brief="Rob another user and take 10% of their balance.",
        example=",rob @user",
    )
    @commands.cooldown(
        1, 60, commands.BucketType.user
    )  # Cooldown of 30 seconds per user
    async def economy_rob(self, ctx, target: discord.Member):
        """Command to rob another user for 10% of their balance."""

        if target.id == ctx.author.id:
            return await ctx.fail("You cannot rob yourself!")

        # Fetch the balance of the target
        target_balance_row = await self.bot.db.fetchrow(
            """SELECT balance FROM economy WHERE user_id = $1""", target.id
        )

        if not target_balance_row:
            return await ctx.fail(
                f"{target.display_name} does not have an economy account!"
            )

        target_balance = target_balance_row["balance"]

        # Convert target balance to an integer and calculate 10%
        target_balance_int = int(target_balance)  # Ensure we're using integers only
        amount_to_steal = target_balance_int // 10  # Use floor division to take 10%

        if amount_to_steal <= 0:
            return await ctx.fail(
                f"{target.display_name} doesn't have enough money to rob."
            )

        # Create the embed for the robbery notification
        rob_embed = discord.Embed(
            title="Robbery Attempt!",
            description=f"{target.mention}, you've been targeted for a robbery by {ctx.author.mention}!\n"
            f"You have **15 seconds** to type anything to stop the robbery!",
            color=self.bot.color,
        )
        rob_embed.set_footer(text="Time is ticking...")

        # Send the robbery notification embed
        rob_message = await ctx.send(embed=rob_embed)

        def check(message):
            return message.author == target  # Accept any message from the target

        try:
            # Wait for the target's response
            response = await self.bot.wait_for("message", check=check, timeout=15.0)
            await rob_message.delete()

            # Target stopped the robbery
            await ctx.fail(f"{target.display_name} successfully stopped the robbery!")
            return

        except asyncio.TimeoutError:
            # If no response from the target in 15 seconds, the robbery succeeds
            await rob_message.delete()

            # Proceed to take the money
            await self.bot.db.execute(
                """UPDATE economy SET balance = balance - $1 WHERE user_id = $2""",
                amount_to_steal,
                target.id,
            )

            await self.bot.db.execute(
                """UPDATE economy SET balance = balance + $1 WHERE user_id = $2""",
                amount_to_steal,
                ctx.author.id,
            )

            await ctx.currency(
                f"You successfully robbed **${amount_to_steal}** 💵 from {target.display_name}!"
            )

    @commands.command(
        name="work", brief="Earn some money by working random jobs.", example=",work"
    )
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def work(self, ctx):
        """Command to simulate working a random job and earning money."""

        # Path to the jobs file (update this path as needed)
        jobs_file_path = "jobs.txt"

        try:
            # Check if the user is a donator
            is_donator = await self.bot.db.fetchrow(
                """SELECT * FROM boosters WHERE user_id = $1""", ctx.author.id
            )

            # Read jobs from the file
            with open(jobs_file_path, "r") as file:
                jobs = [line.strip() for line in file.readlines()]

            if not jobs:
                return await ctx.fail(
                    "No jobs are available at the moment. Please try again later!"
                )

            # Select a random job
            job = random.choice(jobs)

            # Generate a random amount between 500 and 1500
            base_earnings = random.randint(500, 1000)
            multiplier = 2 if is_donator else 1.0  # 3x earnings if donator
            earnings = int(base_earnings * multiplier)

            # Check if the user exists in the economy database
            user_exists = await self.bot.db.fetchrow(
                """SELECT * FROM economy WHERE user_id = $1""", ctx.author.id
            )

            if not user_exists:
                # Insert the user into the economy table if they don't exist
                await self.bot.db.execute(
                    """INSERT INTO economy (user_id, balance, bank) VALUES($1, $2, $3)""",
                    ctx.author.id,
                    0.00,
                    0.00,
                )

            # Update the user's balance
            await self.bot.db.execute(
                """UPDATE economy SET balance = balance + $1 WHERE user_id = $2""",
                earnings,
                ctx.author.id,
            )

            # Send a success message based on donator status
            if is_donator:
                await ctx.currency(
                    f"you worked as a **{job}** and earned **${earnings:,}** 💵! As a booster in [/greedbot](https://discord.gg/greedbot), you received bonus pay for your support!"
                )
            else:
                await ctx.currency(
                    f"you worked as a **{job}** and earned **${earnings:,}** 💵!"
                )

        except FileNotFoundError:
            await ctx.fail(
                "The jobs file is missing. Please contact the administrator."
            )
        except Exception as e:
            await ctx.fail("An error occurred while processing your command.")
            raise e  # Log the exception for debugging purposes

    @commands.command(
        name="beg",
        brief="Earn some money by working the streets.",
        example=",beg",
    )
    @commands.cooldown(
        1, 60, commands.BucketType.user
    )  # Cooldown of 5 seconds per user
    async def beg(self, ctx: commands.Context):
        """Simulate working for a night and earning money with a random result."""

        try:
            # Check if the user is a donator
            is_donator = await self.bot.db.fetchrow(
                """SELECT * FROM boosters WHERE user_id = $1""", ctx.author.id
            )

            # Randomly determine the number of hours worked (1-10 hours)
            worked_hours = random.randint(1, 10)

            # 60% chance to earn more than $100
            if random.random() < 0.6:
                earnings = random.randint(100, 5000)  # Earn between $100 and $5000
            else:
                earnings = random.randint(1, 99)  # Earn between $1 and $99

            # Apply multiplier for boosters (1.2x earnings)
            if is_donator:
                earnings = int(earnings * 1.2)

            # Check if the user exists in the economy database
            user_exists = await self.bot.db.fetchrow(
                """SELECT * FROM economy WHERE user_id = $1""", ctx.author.id
            )

            if not user_exists:
                # Insert the user into the economy table if they don't exist
                await self.bot.db.execute(
                    """INSERT INTO economy (user_id, balance, bank) VALUES($1, $2, $3)""",
                    ctx.author.id,
                    0.00,
                    0.00,
                )

            # Update the user's balance
            await self.bot.db.execute(
                """UPDATE economy SET balance = balance + $1 WHERE user_id = $2""",
                earnings,
                ctx.author.id,
            )

            # Prepare the message based on earnings
            if earnings < 100:
                message = f"Today was a rough night in town. You begged for **{worked_hours}** hours and earned **${earnings:,}** 💵. Better luck next time!"
            elif earnings > 600:
                message = f"Wow! What a night! After begged for **{worked_hours}** hours, you earned a whopping **${earnings:,}!** 💵 You made big money tonight!"
            else:
                message = f"You begged for **{worked_hours}** hours tonight and earned **${earnings:,}** 💵. Not too bad!"

            # Send the message based on donator status
            embed = Embed(description=message, color=0x2A8000)

            if is_donator:
                embed.add_field(
                    name="Bonus",
                    value="As a booster in **[/greedbot](https://discord.gg/greedbot)**, you earned **1.2x** bonus pay for your support!",
                )

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.fail("An error occurred while processing your command.")
            raise e  # Log the exception for debugging purposes

    @commands.command(
        name="crime",
        brief="Attempt a crime for a chance to earn money or get caught!",
        example=",crime",
    )
    @commands.cooldown(
        1, 30, commands.BucketType.user
    )  # Cooldown of 12 seconds per user
    async def crime(self, ctx):
        """Command to simulate committing a crime, possibly earning money or getting caught."""

        crimes_file_path = "crimes.txt"  # Path to the crime list

        try:
            # Read the crimes from the file
            with open(crimes_file_path, "r") as file:
                crimes = [line.strip() for line in file.readlines()]

            if not crimes:
                return await ctx.fail(
                    "No crimes are available at the moment. Please try again later."
                )

            # Select a random crime
            crime = random.choice(crimes)

            # Generate base earnings between 1000 and 5000
            base_earnings = random.randint(1000, 5000)

            # Set the chance of success at 25% (1-25 success, 26-100 failure)
            success_chance = random.randint(1, 100)

            earnings = 0  # Ensure the variable is defined before use
            result_message = ""

            if success_chance <= 45:
                # Crime was successful!
                earnings = base_earnings
                success_messages = [
                    f"you successfully committed **{crime}** and earned **${earnings:,}**!",
                    f"you got away with **{crime}** and made **${earnings:,}**!",
                    f"well done! You managed to pull off **{crime}** and earned **${earnings:,}**!",
                ]
                result_message = random.choice(
                    success_messages
                )  # Pick a random success message
                # Send currency message on success
                await ctx.currency(result_message)
            else:
                # Crime failed, and user gets caught
                earnings = int(
                    base_earnings * 0.5
                )  # They lose 50% of the potential earnings
                failure_messages = [
                    f"you were caught while trying to commit **{crime}** and lost **${earnings:,}** 💵!",
                    f"you got busted for **{crime}** and lost **${earnings:,}** 💵.",
                    f"your attempt to commit **{crime}** failed, and you lost **${earnings:,}** 💵.",
                ]
                result_message = random.choice(
                    failure_messages
                )  # Pick a random failure message
                # Send fail message on failure
                await ctx.fail(result_message)

            # Check if the user exists in the economy database
            user_exists = await self.bot.db.fetchrow(
                """SELECT * FROM economy WHERE user_id = $1""", ctx.author.id
            )

            if not user_exists:
                # If user doesn't exist in the economy table, insert them
                await self.bot.db.execute(
                    """INSERT INTO economy (user_id, balance, bank) VALUES ($1, $2, $3)""",
                    ctx.author.id,
                    0.00,  # Start with 0 balance
                    0.00,  # No bank balance at the start
                )

            # Update the user's balance with the earnings or penalty
            await self.bot.db.execute(
                """UPDATE economy SET balance = balance + $1 WHERE user_id = $2""",
                earnings,
                ctx.author.id,
            )

        except FileNotFoundError:
            await ctx.fail(
                "The crimes file is missing. Please contact the administrator."
            )
        except Exception as e:
            await ctx.fail(
                "An error occurred while committing your crime. Please try again later."
            )
            raise e  # Log the exception for debugging purposes

    @commands.command(name="dance", help="Start a Dance Dance Revolution game!")
    @commands.cooldown(1, 30, commands.BucketType.guild)
    async def dance(self, ctx):
        # Store the ctx object associated with the channel where the game is being played
        self.active_ctx[ctx.channel.id] = ctx
        # Generate a random combo of 5-7 emojis
        combo_length = random.randint(5, 5)
        combo = [random.choice(self.default_emojis) for _ in range(combo_length)]
        combo_str = " ".join(combo)

        # Store the combo for the current channel
        self.active_combos[ctx.channel.id] = combo_str

        # Debugging: Show the generated combo in logs
        logger.info(f"Generated combo: {combo_str} for channel {ctx.channel.id}")

        # Send an embed with the game details
        embed = discord.Embed(
            title="Dance Mode!",
            description=(
                "> **DANCE DANCE REVOLUTION!**\n"
                "> First to send the correct combo in a single message wins.\n"
                "> -# Type the corresponding direction, such as right right left\n\n\n"
                f"**Combo:** {combo_str}"
            ),
            color=self.bot.color,
        )
        embed.set_thumbnail(
            url="https://gifdb.com/images/high/break-dance-meme-cat-sims-game-nfrlhp72lcvdjptq.gif"
        )
        await ctx.send(embed=embed)

        # Wait for 30 seconds and clear the active combo if no winner
        await asyncio.sleep(60)
        if ctx.channel.id in self.active_combos:
            del self.active_combos[ctx.channel.id]
            del self.active_ctx[ctx.channel.id]
            await ctx.send("⏱️ **Time's up!** No one typed the correct combo in time.")
            logger.info(f"Combo timed out for channel {ctx.channel.id}")

    @commands.command(
        name="bombs",
        brief="Play the bombs game - avoid bombs to multiply your bet!",
        example=",bombs 1000 2",
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def bombs(
        self, ctx: commands.Context, amount: GambleAmount, bomb_count: int = 2
    ):
        """Start a bombs game with a grid of tiles and hidden bombs."""
        GRID_SIZE = 4
        total_tiles = GRID_SIZE * GRID_SIZE

        if amount <= 0:
            return await ctx.fail("You must bet a positive amount.")
        if bomb_count <= 0:
            return await ctx.fail("The number of bombs must be at least 1.")
        if bomb_count >= total_tiles:
            return await ctx.fail(f"Too many bombs for {GRID_SIZE}x{GRID_SIZE} grid!")

        balance = await self.bot.db.fetchval(
            "SELECT balance FROM economy WHERE user_id = $1", ctx.author.id
        )
        if balance < amount:
            return await ctx.fail(f"You need {amount-balance:,} more 💵!")

        await self.update_balance(ctx.author, "Take", amount)

        bomb_positions = set(random.sample(range(total_tiles), bomb_count))

        class BombView(View):
            def __init__(self, bot):
                super().__init__(timeout=30)
                self.ctx = ctx
                self.bot = bot
                self.message = None
                self.game_over = False
                self.revealed = set()
                self.multiplier = 1.0
                self.collect_button = None

                # Create a more visually appealing grid with emojis directly on buttons
                for i in range(total_tiles):
                    row = i // GRID_SIZE
                    btn = Button(
                        style=discord.ButtonStyle.secondary, emoji="🎮", row=row
                    )
                    btn.custom_id = f"bomb:{ctx.author.id}:{i}"

                    async def callback(interaction, tile=btn.custom_id.split(":")[-1]):
                        await self.handle_click(interaction, int(tile))

                    btn.callback = callback
                    self.add_item(btn)

                self.collect_button = Button(
                    style=discord.ButtonStyle.success,
                    label=f"Collect ${int(amount * self.multiplier):,}",
                    emoji="💰",
                    row=4,
                )
                self.collect_button.callback = self.handle_collect
                self.add_item(self.collect_button)

            def calculate_multiplier(self):
                """Dynamic multiplier calculation based on game state"""
                revealed_safe = len(self.revealed - bomb_positions)
                remaining_safe = (total_tiles - bomb_count) - revealed_safe

                if remaining_safe <= 1:
                    return 15.0
                if remaining_safe <= 2:
                    return 10.0
                if remaining_safe <= 3:
                    return 7.5

                progress = revealed_safe / (total_tiles - bomb_count)
                difficulty = bomb_count / total_tiles
                return round(1.0 + (difficulty * 5) + (progress * 3), 2)

            def create_embed(self):
                """Generate updated game embed with better formatting"""
                revealed_safe = len(self.revealed - bomb_positions)
                remaining_safe = (total_tiles - bomb_count) - revealed_safe
                potential_win = int(amount * self.multiplier)

                embed = Embed(
                    title="💣 Bombs Game" + (" (GAME OVER)" if self.game_over else ""),
                    color=0x3498DB if not self.game_over else 0xFF0000,
                )

                embed.description = (
                    f"**Avoid the bombs and collect your winnings!**\n\n"
                    f"**Your Bet:** ${amount:,} 💵\n"
                    f"**Current Multiplier:** {self.multiplier:.2f}x\n"
                    f"**Potential Win:** ${potential_win:,} 💵\n"
                    f"**Safe Tiles Remaining:** {remaining_safe}/{total_tiles - bomb_count}"
                )

                if not self.game_over:
                    embed.set_footer(
                        text="Click on tiles to reveal them. Avoid bombs to increase your multiplier!"
                    )

                return embed

            async def handle_click(self, interaction, tile):
                """Process tile reveal"""
                if interaction.user != ctx.author:
                    return await interaction.response.send_message(
                        "This isn't your game!", ephemeral=True
                    )
                if self.game_over or tile in self.revealed:
                    return await interaction.response.defer()

                self.revealed.add(tile)

                button = next(
                    (
                        b
                        for b in self.children
                        if b.custom_id and b.custom_id.endswith(f":{tile}")
                    ),
                    None,
                )
                if button:
                    if tile in bomb_positions:
                        button.emoji = "💣"
                        button.style = discord.ButtonStyle.danger
                        self.game_over = True
                        await self.end_game(
                            interaction, f"**BOOM!** Lost {amount:,} 💵", 0xFF0000
                        )
                        return
                    else:
                        button.emoji = "💰"
                        button.style = discord.ButtonStyle.success
                        button.disabled = True

                self.multiplier = self.calculate_multiplier()
                self.collect_button.label = (
                    f"Collect ${int(amount * self.multiplier):,}"
                )

                revealed_safe = len(self.revealed - bomb_positions)
                remaining_safe = (total_tiles - bomb_count) - revealed_safe

                if remaining_safe <= 0:
                    winnings = int(amount * self.multiplier)
                    await self.update_balance(winnings)
                    await self.end_game(
                        interaction,
                        f"**CLEARED!** Won {winnings:,} 💵!",
                        self.bot.color,
                    )
                    return

                await interaction.response.edit_message(
                    embed=self.create_embed(), view=self
                )

            async def handle_collect(self, interaction):
                """Process collect action"""
                if interaction.user != ctx.author:
                    return await interaction.response.send_message(
                        "This isn't your game!", ephemeral=True
                    )

                winnings = int(amount * self.multiplier)
                await self.update_balance(winnings)
                await self.end_game(
                    interaction, f"**COLLECTED!** Won {winnings:,} 💵!", self.bot.color
                )

            async def end_game(self, interaction, description, color):
                """Cleanup game ending"""
                self.game_over = True

                for i, button in enumerate(self.children):
                    if (
                        hasattr(button, "custom_id")
                        and button.custom_id
                        and button.custom_id.startswith("bomb:")
                    ):
                        tile_id = int(button.custom_id.split(":")[-1])
                        if tile_id in bomb_positions:
                            button.emoji = "💣"
                            button.style = discord.ButtonStyle.danger
                        elif tile_id not in self.revealed:
                            button.emoji = "⬜"
                        button.disabled = True

                self.collect_button.disabled = True

                embed = self.create_embed()
                embed.description = description
                embed.color = color

                await interaction.response.edit_message(embed=embed, view=self)
                self.stop()

            async def update_balance(self, winnings):
                """Update player balance"""
                await self.bot.db.execute(
                    "UPDATE economy SET balance = balance + $1 WHERE user_id = $2",
                    winnings,
                    ctx.author.id,
                )

            async def on_timeout(self):
                """Handle game timeout"""
                if not self.game_over:
                    for item in self.children:
                        item.disabled = True
                    await self.message.edit(view=self)
                    await self.ctx.send(f"{ctx.author.mention} Game timed out!")

        view = BombView(self.bot)
        view.message = await ctx.send(embed=view.create_embed(), view=view)

    @commands.command(
        name="crack", description="Play Crack to unlock the safe and earn money."
    )
    @commands.cooldown(1, 30, commands.BucketType.guild)
    async def crack(self, ctx):
        progress = 0.0
        avatar_b64 = base64.b64encode(await ctx.author.display_avatar.read()).decode(
            "utf-8"
        )  # Avatar in base64

        difficulty_choices = {
            "easy": self.generate_easy_question,
            "medium": self.generate_medium_question,
            "hard": self.generate_hard_question,
        }

        await ctx.send("-# Choose a difficulty: **easy, medium, or hard.**")

        def check(msg):
            return (
                msg.author == ctx.author
                and msg.channel == ctx.channel
                and msg.content.lower() in difficulty_choices
            )

        try:
            difficulty_msg = await self.bot.wait_for(
                "message", timeout=10.0, check=check
            )
            difficulty = difficulty_msg.content.lower()

            safe_amount = self.get_random_amount(difficulty)
            progress_per_question = 1 / 5

            message = await ctx.send(
                "-# Answer the following questions to unlock the safe."
            )

            for _ in range(5):
                question_func = difficulty_choices[difficulty]
                question, answer = question_func()
                await asyncio.sleep(1.8)

                await message.edit(content=question)

                def answer_check(m):
                    return m.author == ctx.author and m.channel == ctx.channel

                try:
                    response = await self.bot.wait_for(
                        "message", timeout=30.0, check=answer_check
                    )

                    if response.content.isdigit() and int(response.content) == answer:
                        progress += progress_per_question

                        buffer = self.generate_pie_chart(
                            ctx.author.name, progress, avatar_b64
                        )
                        file = discord.File(
                            buffer, filename=f"{ctx.author.name}_safe_progress.png"
                        )

                        await message.edit(
                            content=f"-# Correct! Progress: **{int(progress * 100)}%**",
                            attachments=[file],
                        )

                    else:
                        incorrect_msg = await ctx.send(
                            "-# Incorrect answer, the game has stopped."
                        )
                        await asyncio.sleep(3)
                        await incorrect_msg.delete()
                        await message.delete()
                        break

                except asyncio.TimeoutError:
                    timeout_msg = await ctx.send("-# Time's up! The game has stopped.")
                    await asyncio.sleep(3)  # Wait 3 seconds before deleting
                    await timeout_msg.delete()  # Delete the timeout message
                    await message.delete()  # Delete the question message
                    break  # Exit the loop

            # Final result after all questions (or game stop)
            earnings = int(
                progress * safe_amount
            )  # Calculate earnings based on progress and safe amount
            await self.bot.db.execute(
                """UPDATE economy SET balance = balance + $1 WHERE user_id = $2""",
                earnings,
                ctx.author.id,
            )
            await ctx.currency(
                f"Game over! You earned **${earnings}** credits from the safe!"
            )

        except asyncio.TimeoutError:
            await ctx.fail(
                "You took too long to select a difficulty. Please try again."
            )
            await message.delete()

    @commands.command(
        name="fish", description="Go fishing and catch a random fish for money!"
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def fish(self, ctx):
        # Define different fish with their rarity and price (rarity is a value from 1 to 100, higher rarity = rarer)
        fish_data = {
            # Common Fish (rarity between 0.6 - 0.9)
            "Goldfish": {"rarity": 0.80, "price": 100},
            "Salmon": {"rarity": 0.60, "price": 200},
            "Tuna": {"rarity": 0.50, "price": 400},
            "Bass": {"rarity": 0.70, "price": 150},
            "Trout": {"rarity": 0.65, "price": 300},
            "Catfish": {"rarity": 0.55, "price": 500},
            "Swordfish": {"rarity": 0.35, "price": 1000},
            "Shark": {"rarity": 0.10, "price": 5000},
            "Piranha": {"rarity": 0.45, "price": 600},
            "Mackerel": {"rarity": 0.75, "price": 200},
            "Angelfish": {"rarity": 0.85, "price": 50},
            "Carp": {"rarity": 0.65, "price": 150},
            "Sturgeon": {"rarity": 0.25, "price": 800},
            "Lobster": {"rarity": 0.15, "price": 1500},
            "Jellyfish": {"rarity": 0.10, "price": 2500},
            "Marlin": {"rarity": 0.08, "price": 7000},
            "Rainbow Trout": {"rarity": 0.60, "price": 350},
            "Tilapia": {"rarity": 0.55, "price": 400},
            "Cod": {"rarity": 0.70, "price": 120},
            # Medium Rarity Fish (rarity between 0.4 - 0.6)
            "Bluegill": {"rarity": 0.50, "price": 5500},
            "Perch": {"rarity": 0.55, "price": 6000},
            "Bass Catfish": {"rarity": 0.60, "price": 7000},
            "Bream": {"rarity": 0.50, "price": 5500},
            "Yellowtail": {"rarity": 0.45, "price": 6000},
            "Snapper": {"rarity": 0.48, "price": 6500},
            "Pike": {"rarity": 0.52, "price": 7000},
            "Squid": {"rarity": 0.47, "price": 7000},
            "Mahi-Mahi": {"rarity": 0.55, "price": 7500},
            "Barracuda": {"rarity": 0.49, "price": 8000},
            # High Rarity Fish (rarity between 0.2 - 0.4)
            "King Salmon": {"rarity": 0.30, "price": 9000},
            "Stingray": {"rarity": 0.25, "price": 9500},
            "Swordfish Shark": {"rarity": 0.15, "price": 10000},
            "Tiger Shark": {"rarity": 0.18, "price": 12000},
            "Giant Squid": {"rarity": 0.20, "price": 13000},
            "Great White Shark": {"rarity": 0.12, "price": 15000},
            "Blue Marlin": {"rarity": 0.22, "price": 17000},
            "Goliath Grouper": {"rarity": 0.17, "price": 19000},
            "Golden Trout": {"rarity": 0.19, "price": 20000},
            "Flying Fish": {"rarity": 0.28, "price": 22000},
            # Ultra Rarity Fish (rarity between 0.01 - 0.20)
            "Leopard Shark": {"rarity": 0.10, "price": 25000},
            "Titanic Squid": {"rarity": 0.05, "price": 30000},
            "Emperor Angelfish": {"rarity": 0.08, "price": 35000},
            "Whale Shark": {"rarity": 0.03, "price": 40000},
            "Arowana": {"rarity": 0.15, "price": 50000},
            "Electric Eel": {"rarity": 0.06, "price": 55000},
            "Caviar Sturgeon": {"rarity": 0.04, "price": 60000},
            "Sunfish": {"rarity": 0.07, "price": 65000},
            "Deep-Sea Anglerfish": {"rarity": 0.02, "price": 70000},
            "Megalodon Tooth Fish": {"rarity": 0.01, "price": 100000},
        }

        # Show the loading message while the user fishes
        fishing_embed = discord.Embed(
            title="<:fishsus:1337411037594386493> Fishing...",
            description="You cast your line, waiting for something to bite <a:loading2:1337411183195717713>",
            color=self.bot.color,
        )
        fishing_message = await ctx.send(embed=fishing_embed)

        # Simulate a fishing delay
        await asyncio.sleep(3.5)  # Wait for 2.4 seconds before showing the caught fish

        # Randomly determine which fish the user catches based on rarity
        fish_choice = random.choices(
            list(fish_data.keys()),
            weights=[fish_data[fish]["rarity"] for fish in fish_data],
            k=1,
        )[0]

        # Get the fish price
        fish_price = fish_data[fish_choice]["price"]

        # Create a new embed with the caught fish and the money earned
        caught_embed = discord.Embed(
            title="🎣 You Caught a Fish!",
            description=f"Congratulations! You caught a **{fish_choice}** and earned **${fish_price}** 💵!",
            color=self.bot.color,
        )
        await fishing_message.edit(embed=caught_embed)

        # Update the user's fish caught history in the database
        user_fish = await self.bot.db.fetchval(
            """
            SELECT fish_caught FROM user_fish WHERE user_id = $1
        """,
            ctx.author.id,
        )

        if user_fish:
            user_fish += f", {fish_choice}"
        else:
            user_fish = fish_choice

        await self.bot.db.execute(
            """
            INSERT INTO user_fish (user_id, fish_caught) 
            VALUES ($1, $2) 
            ON CONFLICT(user_id) 
            DO UPDATE SET fish_caught = $2
        """,
            ctx.author.id,
            user_fish,
        )

        # Update the user's balance
        await self.bot.db.execute(
            """UPDATE economy SET balance = balance + $1 WHERE user_id = $2""",
            fish_price,
            ctx.author.id,
        )

    @commands.command(name="myfish", description="Show the list of fish you've caught.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def myfish(self, ctx):
        """Display all the fish the user has caught."""
        # Retrieve the user's caught fish data from the database
        user_fish_data = await self.bot.db.fetchval(
            """
            SELECT fish_caught FROM user_fish WHERE user_id = $1
            """,
            ctx.author.id,
        )
    
        # Determine the user's avatar URL (fallback to default avatar if none exists)
        avatar_url = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
    
        if user_fish_data:
            # Split the caught fish string and count occurrences
            fish_list = user_fish_data.split(", ")
            fish_count = {}
            for fish in fish_list:
                fish_count[fish] = fish_count.get(fish, 0) + 1
    
            # Build the list of caught fish with their quantities
            fish_list_display = "\n".join(
                [f"**{fish}**: {count}x" for fish, count in fish_count.items()]
            )
    
            # Create the embed message
            fish_embed = discord.Embed(
                title=f"{ctx.author.name}'s Caught Fish",
                description=f"You've caught the following fish:\n{fish_list_display}",
                color=self.bot.color,
            )
            fish_embed.set_thumbnail(
                url="https://i.seadn.io/gae/6E1B1A-8Q2h-9ddUhJGMmH4Vdfz_8VMmYDcLBy1lSq5HtSuvBF6vYeZF1csYAqttATn98mzBVE6qOg51tGiHXIidu_Bopwuez0lOHw?auto=format&dpr=1&w=1000"
            )  # Replace with the actual fish PNG URL
            fish_embed.set_author(name=ctx.author.name, icon_url=avatar_url)
    
            await ctx.send(embed=fish_embed)
        else:
            # Create the embed message when no fish are caught
            no_fish_embed = discord.Embed(
                title=f"{ctx.author.name}'s Caught Fish",
                description="You haven't caught any fish yet!",
                color=self.bot.color,
            )
            no_fish_embed.set_thumbnail(
                url="https://i.seadn.io/gae/6E1B1A-8Q2h-9ddUhJGMmH4Vdfz_8VMmYDcLBy1lSq5HtSuvBF6vYeZF1csYAqttATn98mzBVE6qOg51tGiHXIidu_Bopwuez0lOHw?auto=format&dpr=1&w=1000"
            )  # Replace with the actual fish PNG URL
            no_fish_embed.set_author(name=ctx.author.name, icon_url=avatar_url)
    
            await ctx.send(embed=no_fish_embed)

    @commands.group(invoke_without_command=True)
    async def lab(self, ctx):
        """Lab command group."""
        return await ctx.send_help(ctx.command.qualified_name)

    @lab.command()
    async def buy(self, ctx):
        """Buy a laboratory business."""

        user_lab = await self.get_lab(ctx.author.id)
        if user_lab:
            return await ctx.fail("You already own a laboratory!")

        balance = await self.bot.db.fetchval(
            "SELECT balance FROM economy WHERE user_id = $1", ctx.author.id
        )
        cost = 5_000_000  # 5 million

        if balance < cost:
            return await ctx.fail(
                f"You do not have enough cash to buy a laboratory.\nYou need **{cost:,}** 💵"
            )

        await self.bot.db.execute(
            "UPDATE economy SET balance = balance - $1 WHERE user_id = $2",
            cost,
            ctx.author.id,
        )
        await self.bot.db.execute(
            "INSERT INTO labs (user_id) VALUES ($1)", ctx.author.id
        )

        await ctx.success(
            f"You have successfully bought a **Laboratory**! <:ampoule:1337841915177205875>"
        )

    @lab.command()
    async def upgrade(self, ctx):
        """Upgrade your laboratory storage."""

        user_lab = await self.get_lab(ctx.author.id)
        if not user_lab:
            return await ctx.fail("You do not own a laboratory! Use `lab buy` first.")

        level = user_lab["level"]
        upgrade_cost = 329_142 * level
        storage_increase = 164_571

        balance = await self.bot.db.fetchval(
            "SELECT balance FROM economy WHERE user_id = $1", ctx.author.id
        )
        if balance < upgrade_cost:
            return await ctx.fail(
                f"You do not have enough cash to upgrade.\nYou need **{upgrade_cost:,}** 💵"
            )

        new_storage = user_lab["storage"] + storage_increase
        await self.bot.db.execute(
            "UPDATE economy SET balance = balance - $1 WHERE user_id = $2",
            upgrade_cost,
            ctx.author.id,
        )
        await self.update_lab(ctx.author.id, level=level + 1, storage=new_storage)

        await ctx.success(
            f"Your **Laboratory** has been upgraded to Level **{level + 1}**! 📈"
        )

    @lab.command()
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def ampoules(self, ctx, amount: int):
        """Buy ampoules for your laboratory."""

        if amount < 1 or amount > 5:

            return await ctx.fail(
                "You can only buy between **1** and **5** ampoules at a time!"
            )

        user_lab = await self.get_lab(ctx.author.id)
        if not user_lab:
            return await ctx.fail("You do not own a laboratory! Use `lab buy` first.")

        max_ampoules = 50
        current_ampoules = user_lab.get("ampoules", 1)
        if current_ampoules + amount > max_ampoules:
            return await ctx.fail(
                f"You already have the maximum **{max_ampoules}** ampoules."
            )

        cost_per_ampoule = 10_276
        total_cost = amount * cost_per_ampoule

        balance = await self.bot.db.fetchval(
            "SELECT balance FROM economy WHERE user_id = $1", ctx.author.id
        )
        if balance < total_cost:
            return await ctx.fail(
                f"You do not have enough cash to buy **{amount}** ampoules.\nTotal cost: **{total_cost:,}** 💵"
            )

        new_ampoules = user_lab["ampoules"] + amount
        await self.bot.db.execute(
            "UPDATE economy SET balance = balance - $1 WHERE user_id = $2",
            total_cost,
            ctx.author.id,
        )
        await self.update_lab(ctx.author.id, ampoules=new_ampoules)

        await ctx.success(
            f"You bought **{amount}** ampoules! Your earnings per hour increased. <:ampoule:1337841915177205875>"
        )

    @lab.command()
    async def collect(self, ctx):
        """Collect your laboratory business earnings."""

        user_lab = await self.get_lab(ctx.author.id)
        if not user_lab:
            return await ctx.fail("You do not own a laboratory! Use `lab buy` first.")

        earnings = user_lab["earnings"]
        if earnings == 0:
            return await ctx.fail("You have no earnings to collect.")

        await self.bot.db.execute(
            "UPDATE economy SET balance = balance + $1 WHERE user_id = $2",
            earnings,
            ctx.author.id,
        )
        await self.update_lab(ctx.author.id, earnings=0)

        await ctx.success(
            f"You collected **{earnings:,}** 💵 from your laboratory! <:ampoule:1337841915177205875>"
        )

    @lab.command()
    async def status(self, ctx):
        """Check the status of your laboratory business."""

        user_lab = await self.get_lab(ctx.author.id)
        if not user_lab:
            return await ctx.fail("You do not own a laboratory! Use `lab buy` first.")

        level = user_lab["level"]
        ampoules = user_lab["ampoules"]
        earnings = user_lab["earnings"]
        storage = user_lab["storage"]
        earnings_per_hour = ampoules * 3_276
        next_upgrade_cost = 329_142 * level

        embed = discord.Embed(title="Laboratory Status", color=self.bot.color)
        embed.add_field(
            name="Ampoules <:ampoule:1337841915177205875>",
            value=f"```{ampoules:,}```",
            inline=True,
        )
        embed.add_field(name="Upgrade State", value=f"```{level}```", inline=True)
        embed.add_field(
            name="Earnings per Hour",
            value=f"```💵 {earnings_per_hour:,}```",
            inline=False,
        )
        embed.add_field(
            name="Next Upgrade Cost",
            value=f"```💵 {next_upgrade_cost:,}```",
            inline=False,
        )
        embed.add_field(
            name="Current Earnings", value=f"```💵 {earnings:,}```", inline=True
        )
        embed.add_field(
            name="Storage Limit", value=f"```💵 {storage:,}```", inline=True
        )
        await ctx.send(embed=embed)

    @commands.command(
        name="scratch",
        brief="Buy a scratch card and test your luck",
        example=",scratch 1000",
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    @account()
    async def scratch(self, ctx: commands.Context, amount: GambleAmount):
        """
        Buy a scratch card with 9 covered squares.
        Match 3 symbols to win:
        - 💎 (10x)
        - 💰 (5x)
        - 🎲 (3x)
        - 🎯 (2x)
        """
        balance = await self.bot.db.fetchval(
            "SELECT balance FROM economy WHERE user_id = $1", ctx.author.id
        )

        if balance < amount:
            return await ctx.fail(
                f"You don't have enough money! Your balance is ${balance:,}"
            )

        await self.update_balance(ctx.author, "Take", amount)

        symbols = {"💎": 10, "💰": 5, "🎲": 3, "🎯": 2}

        grid_symbols = []
        symbol_list = list(symbols.keys())

        winning_symbol = None
        will_win = random.random() < 0.2

        if will_win:
            winning_symbol = random.choice(symbol_list)
            winning_positions = random.sample(range(9), 3)

            for i in range(9):
                if i in winning_positions:
                    grid_symbols.append(winning_symbol)
                else:
                    random_symbol = random.choice(symbol_list)
                    while (
                        random_symbol == winning_symbol
                        and grid_symbols.count(winning_symbol) >= 2
                    ):
                        random_symbol = random.choice(symbol_list)
                    grid_symbols.append(random_symbol)
        else:
            for i in range(9):
                available_symbols = symbol_list.copy()

                for symbol in symbol_list:
                    if grid_symbols.count(symbol) >= 2:
                        if symbol in available_symbols:
                            available_symbols.remove(symbol)

                if not available_symbols:
                    symbol_counts = {s: grid_symbols.count(s) for s in symbol_list}
                    min_count = min(symbol_counts.values())
                    least_common = [
                        s for s, c in symbol_counts.items() if c == min_count
                    ]
                    grid_symbols.append(random.choice(least_common))
                else:
                    grid_symbols.append(random.choice(available_symbols))

        class ScratchCardView(discord.ui.View):
            def __init__(self, ctx, bot, grid_symbols, amount, symbols):
                super().__init__(timeout=60)
                self.ctx = ctx
                self.bot = bot
                self.grid_symbols = grid_symbols
                self.amount = amount
                self.symbols = symbols
                self.scratched = [False] * 9
                self.message = None
                self.game_ended = False

                for i in range(9):
                    row = i // 3
                    button = discord.ui.Button(
                        label="❓",
                        style=discord.ButtonStyle.secondary,
                        row=row,
                        custom_id=str(i),
                    )
                    button.callback = self.scratch_callback
                    self.add_item(button)

            async def scratch_callback(self, interaction: discord.Interaction):
                if interaction.user != self.ctx.author:
                    return await interaction.response.send_message(
                        "This isn't your scratch card!", ephemeral=True
                    )

                if self.game_ended:
                    return await interaction.response.defer()

                button_idx = int(interaction.data["custom_id"])

                self.scratched[button_idx] = True

                await self.update_view(interaction)

                await self.check_win(interaction)

            async def update_view(self, interaction):
                for i, (button, scratched) in enumerate(
                    zip(self.children[:9], self.scratched)
                ):
                    if scratched:
                        button.label = self.grid_symbols[i]
                        button.disabled = True

                await interaction.response.edit_message(
                    embed=self.get_embed(), view=self
                )

            async def check_win(self, interaction=None):
                if self.game_ended:
                    return

                symbol_counts = {}
                for i, scratched in enumerate(self.scratched):
                    if scratched:
                        symbol = self.grid_symbols[i]
                        symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1

                for symbol, count in symbol_counts.items():
                    if count >= 3:
                        self.game_ended = True
                        multiplier = self.symbols[symbol]
                        winnings = int(self.amount * multiplier)

                        await self.bot.db.execute(
                            "UPDATE economy SET balance = balance + $1 WHERE user_id = $2",
                            winnings,
                            self.ctx.author.id,
                        )

                        for button in self.children:
                            button.disabled = True

                        self.scratched = [True] * 9
                        for i, button in enumerate(self.children[:9]):
                            button.label = self.grid_symbols[i]

                        win_embed = discord.Embed(
                            title="🎊 Scratch Card Winner! 🎊",
                            description=f"You matched 3 {symbol} symbols and won **${winnings:,}**!\n"
                            f"Multiplier: {multiplier}x",
                            color=0x2ECC71,
                        )

                        if interaction:
                            await interaction.edit_original_response(
                                embed=win_embed, view=self
                            )
                        elif self.message:
                            await self.message.edit(embed=win_embed, view=self)
                        return True

                if all(self.scratched) and not self.game_ended:
                    self.game_ended = True
                    for button in self.children:
                        button.disabled = True

                    loss_embed = discord.Embed(
                        title="❌ Scratch Card - No Match",
                        description=f"You didn't match 3 symbols. Better luck next time!\n"
                        f"You lost **${self.amount:,}**.",
                        color=0xE74C3C,
                    )

                    if interaction:
                        await interaction.edit_original_response(
                            embed=loss_embed, view=self
                        )
                    elif self.message:
                        await self.message.edit(embed=loss_embed, view=self)
                    return False

                return False

            def get_embed(self):
                embed = discord.Embed(
                    title="🎫 Scratch Card",
                    description=f"Scratch to reveal symbols. Match 3 to win!\n"
                    f"Cost: **${self.amount:,}**\n\n"
                    f"Rewards:\n"
                    f"- 💎 = 10x\n"
                    f"- 💰 = 5x\n"
                    f"- 🎲 = 3x\n"
                    f"- 🎯 = 2x",
                    color=self.ctx.bot.color,
                )
                return embed

            async def on_timeout(self):
                if not self.game_ended:
                    for button in self.children:
                        button.disabled = True

                    timeout_embed = discord.Embed(
                        title="⏰ Scratch Card - Timed Out",
                        description="The scratch card game timed out. All squares have been revealed.",
                        color=0xF39C12,
                    )

                    self.scratched = [True] * 9
                    for i, button in enumerate(self.children[:9]):
                        button.label = self.grid_symbols[i]

                    await self.message.edit(embed=timeout_embed, view=self)

                    await self.check_win()

        view = ScratchCardView(ctx, self.bot, grid_symbols, amount, symbols)
        embed = view.get_embed()
        view.message = await ctx.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(Economy(bot))
