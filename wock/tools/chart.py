from asyncio import to_thread as thread
from datetime import datetime
from io import BytesIO
from typing import List, Union

import pandas as pd  # type: ignore
import plotly.graph_objects as go  # type: ignore
from discord import Member  # type: ignore
from discord import Embed, File  # type: ignore
from discord.ext.commands import Context  # type: ignore
from pytz import timezone  # type: ignore
from rival_tools import timeit  # type: ignore # type: ignore


def format_large(num: Union[int, float]) -> str:
    if str(num).startswith("-"):
        symbol = "-"
    else:
        symbol = ""
    num = int(float(str(num).replace("-", "")))
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
    num = int(float(num))
    # Number of digits in the input number
    num_str = str(num)
    if "." in num_str:
        num_str = num_str[: num_str.index(".")]
    num_len = len(num_str)

    # Determine the appropriate suffix and scale the number
    if num_len <= 3:
        return (
            f"{symbol}{num_str}"  # No suffix needed for numbers with 3 or fewer digits
        )

    # Calculate the index for suffixes list
    suffix_index = (num_len - 1) // 3

    if suffix_index >= len(suffixes):
        return f"{num} is too large to format."

    # Calculate the formatted number
    scaled_num = int(num_str[: num_len - suffix_index * 3])

    return f"{symbol}{scaled_num}{suffixes[suffix_index]}"


class EconomyCharts:
    def __init__(self, bot):
        self.bot = bot

    def format_large_number(self, number_str: Union[float, str, int]):
        number_str = str(number_str)
        if number_str.startswith("-"):
            sign = "-"
            number_str = number_str[1:]
        else:
            sign = ""
        reversed_number = number_str[::-1]
        chunks = [reversed_number[i : i + 3] for i in range(0, len(reversed_number), 3)]
        formatted_number = ",".join(chunks)[::-1]
        if ",." in formatted_number:
            formatted_number = formatted_number.replace(",.", ".")
        return sign + formatted_number

    def format_int(self, n: Union[float, str, int]):
        emoji = None
        bal = None
        if isinstance(n, float):
            n = "{:.2f}".format(n)
        if isinstance(n, str):
            if "." in n:
                try:
                    amount, decimal = n.split(".")
                    n = f"{amount}.{decimal[:2]}"
                except Exception:
                    n = f"{n.split('.')[0]}.00"
        #        if str(n).startswith("-"):
        #           return f":clown: ${n}"
        n_ = str(n).split(".")[0]
        if len(str(n_)) >= 10:
            if str(n_).startswith("-"):
                emoji = "<:downtriangle:1221951843463200798>"
            else:
                emoji = "<:uptriangle:1221951842250915992>"
            return f"{emoji} {format_large(float(n))}"
        n = str(n).replace("-0.00", "0")
        n = self.format_large_number(n)
        if n.startswith("-"):
            emoji = "<:downtriangle:1221951843463200798>"
        else:
            emoji = "<:uptriangle:1221951842250915992>"
        return f"{emoji} {n}"
        reversed = str(n).split(".")[0][::-1]  # type: ignore
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
            if "-" in d[::-1]:
                bal = d[::][1:].replace("-,", "-")
                emoji = "<:downtriangle:1221951843463200798>"
            else:
                emoji = "<:uptriangle:1221951842250915992>"
                bal = d[::-1][1:]
        else:
            if d[::-1].startswith("-"):
                bal = d[::-1].replace("-,", "-")
                emoji = "<:downtriangle:1221951843463200798>"
            else:
                emoji = "<:uptriangle:1221951842250915992>"
                bal = d[::-1]
        if emoji is None:
            if bal is None:
                return d[::-1]
            else:
                return bal
        else:
            if bal is None:
                bal = d[::-1]
            return f"{emoji} {bal}"

    def get_percent(self, amount: int, total: int):
        if not amount > 0:
            return "0"
        else:
            return int(amount / total * 100)

    async def chart_earnings(self, ctx: Context, member: Member):
        if rec := await self.bot.db.fetchval(
            f"SELECT h{datetime.now(timezone('US/Eastern')).hour+1} FROM earnings WHERE user_id = $1",
            member.id,
        ):
            recent = rec
        else:
            recent = 0
        data = await self.bot.db.fetchrow(
            "SELECT h1,h2,h3,h4,h5,h6,h7,h8,h9,h10,h11,h12,h13,h14,h15,h16,h17,h18,h19,h20,h21,h22,h23,h24,h25 FROM earnings WHERE user_id = $1",
            member.id,
        )
        if not data:
            await self.bot.db.execute(
                """INSERT INTO earnings (user_id,h1,h2,h3,h4,h5,h6,h7,h8,h9,h10,h11,h12,h13,h14,h15,h16,h17,h18,h19,h20,h21,h22,h23,h24,h25) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22,$23,$24,$25,$26)""",
                member.id,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
            )
            data = [
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
            ]
        labels = [str(hour) for hour in range(1, 25)]
        profits = [float(i) for i in data]
        earnings = float(
            await self.bot.db.fetchval(
                """SELECT earnings FROM economy WHERE user_id = $1""", member.id
            )
        )
        rank = [
            row.user_id
            for row in await self.bot.db.fetch(
                """SELECT user_id FROM economy ORDER BY earnings DESC"""
            )
        ]
        try:
            rank = rank.index(member.id) + 1
        except Exception:
            rank = 0

        def make_chart(labels: List[str], profits: List[float]):
            buffer = BytesIO()
            df = pd.DataFrame({"Earnings": profits})

            # Create line chart
            fig = go.Figure(data=go.Scatter(x=df.index, y=df["Earnings"], mode="lines"))
            fig.update_traces(line=dict(color="lime"))
            # Update chart layout
            fig.update_layout(
                title="Earnings Graph",
                xaxis_title="TimeFrame",
                yaxis_title="Price",
                width=1200,
                plot_bgcolor="black",  # Set background color to black
                paper_bgcolor="black",
                margin=dict(l=100, r=100, t=100, b=100),
                # , # Set paper color to black
                yaxis=dict(showgrid=False),
                font=dict(color="white"),  # Set font color to white
                xaxis=dict(
                    tickmode="array",
                    tickvals=df.index,
                    tickangle=0,
                    showgrid=False,
                    ticktext=labels,
                ),
            )  # Set tick values to every hour
            fig.update_layout(
                {
                    "plot_bgcolor": "rgba(0, 0, 0, 0)",
                    "paper_bgcolor": "rgba(0, 0, 0, 0)",
                }
            )
            # Show the chart
            fig.write_image(buffer, format="png")
            buffer.seek(0)
            return buffer

        async with timeit():  # type: ignore
            chart = await thread(make_chart, labels, profits)
        file = File(fp=chart, filename="chart.png")
        balance, bank, wins, total = await self.bot.db.fetchrow(
            """SELECT balance, bank, wins, total FROM economy WHERE user_id = $1""",
            member.id,
        )
        balance = self.format_int(float(balance))
        bank = self.format_int(float(bank))
        percentage = self.get_percent(int(wins), int(total))
        return await ctx.send(
            embed=Embed(title=f"{member.name}'s profit", color=self.bot.color)
            .set_image(url=f"attachment://{file.filename}")
            .add_field(name="Earnings", value=self.format_int(earnings), inline=True)
            .add_field(name="Recent Earned", value=self.format_int(recent), inline=True)
            .add_field(name="W/L", value=f"{percentage}%", inline=True)
            .add_field(name="Balance", value=balance, inline=True)
            .add_field(name="Bank", value=bank, inline=True)
            .add_field(
                name="Rank", value=f"{rank if rank > 0 else 'unranked'}", inline=True
            ),
            file=file,
        )
