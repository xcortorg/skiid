import plotly.graph_objects as go
import discord

from discord.ui import View
from discord import ButtonStyle

from config import EMOJIS

from typing import Union, Optional, Dict
from datetime import datetime, timedelta
from discord import Member, File, Embed
from pytz import timezone
from io import BytesIO

class EconomyCharts:
    def __init__(self, bot):
        self.bot = bot
        self.cache = {}
        self.est = timezone('US/Eastern')

    def format_currency(self, amount: Union[int, float, str]) -> str:
        try:
            num = float(str(amount).replace(",", ""))
        except ValueError:
            return "0"
            
        is_negative = num < 0
        abs_num = abs(num)
        
        if abs_num >= 1_000_000_000:  
            formatted = f"{abs_num/1_000_000_000:.1f}B"
        elif abs_num >= 1_000_000: 
            formatted = f"{abs_num/1_000_000:.1f}M"
        elif abs_num >= 1_000: 
            formatted = f"{abs_num/1_000:.1f}K"
        else:
            formatted = f"{abs_num:,.0f}"
            
        emoji = EMOJIS.ECONOMY.DOWN if is_negative else EMOJIS.ECONOMY.UP
        return f"{emoji} {formatted}"

    def get_win_rate(self, wins: int, total: int) -> str:
        return "0%" if not total else f"{(wins/total * 100):.1f}%"

    async def get_user_data(self, member_id: int) -> Optional[Dict]:
        data = await self.bot.db.fetchrow("""
            SELECT 
                e.balance, e.bank, e.wins, e.total, e.earnings,
                (SELECT COALESCE(SUM(CASE WHEN action = 'Add' THEN amount ELSE -amount END), 0)
                 FROM transactions 
                 WHERE user_id = e.user_id 
                 AND timestamp >= NOW() - INTERVAL '24 hours') as daily_earnings,
                (SELECT COALESCE(SUM(CASE WHEN action = 'Add' THEN amount ELSE -amount END), 0)
                 FROM transactions 
                 WHERE user_id = e.user_id 
                 AND timestamp >= NOW() - INTERVAL '1 hour') as hourly_earnings
            FROM economy e
            WHERE e.user_id = $1
        """, member_id)

        return dict(data) if data else None

    async def generate_smooth_chart(self, member_id: int, timeframe: str = "24h"):
        """Generate smoothed earnings chart for the specified timeframe"""
        
        if timeframe == "24h":
            interval = "hour"
            points = 24
            format_str = "%H:00"
            interval_str = "24 hours"
            show_every_nth = 2 
        elif timeframe == "14d":
            interval = "day"
            points = 14
            format_str = "%d %b"
            interval_str = "14 days"
            show_every_nth = 1
        else: 
            interval = "day"
            points = 30
            format_str = "%d %b"
            interval_str = "30 days"
            show_every_nth = 1

        earnings_data = await self.bot.db.fetch(f"""
            SELECT 
                date_trunc('{interval}', timestamp) as time_period,
                SUM(CASE WHEN action = 'Add' THEN amount ELSE -amount END) as earnings
            FROM transactions 
            WHERE user_id = $1 
                AND timestamp >= NOW() - INTERVAL '{interval_str}'
            GROUP BY time_period 
            ORDER BY time_period ASC
            LIMIT {points}
        """, member_id)

        now = datetime.now(self.est)
        times = []
        earnings = [0] * points

        for i in range(points):
            if timeframe == "24h":
                time_point = now - timedelta(hours=i)
            else:
                time_point = now - timedelta(days=i)
            times.append(time_point.strftime(format_str))
            
            for row in earnings_data:
                if row['time_period'].replace(tzinfo=self.est).strftime(format_str) == time_point.strftime(format_str):
                    earnings[i] = row['earnings']
                    break

        times.reverse()
        earnings.reverse()

        display_times = []
        display_positions = []
        for i, time in enumerate(times):
            if i % show_every_nth == 0:
                display_times.append(time)
                display_positions.append(i)

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=list(range(len(times))),
            y=earnings,
            mode='lines',
            line=dict(
                color="#00ff00",
                width=2,
                shape='spline',  
                smoothing=1.3  
            ),
            fill='tozeroy',
            fillcolor="rgba(0,255,0,0.1)"
        ))

        fig.update_layout(
            title=dict(
                text=f"{interval_str.title()} Earnings",
                font=dict(size=24, color="white"),
                x=0.5
            ),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(
                title="Time",
                gridcolor="rgba(255,255,255,0.1)",
                tickfont=dict(color="white"),
                ticktext=display_times,
                tickvals=display_positions,
                showgrid=True,
                tickangle=45 if timeframe != "24h" else 0
            ),
            yaxis=dict(
                title="Amount",
                gridcolor="rgba(255,255,255,0.1)",
                tickfont=dict(color="white"),
                showgrid=True,
                tickformat=",.0f"
            ),
            width=1000,
            height=500,
            margin=dict(l=80, r=80, t=100, b=80 if timeframe != "24h" else 60),
            showlegend=False,
            hovermode='x unified'
        )

        buffer = BytesIO()
        fig.write_image(buffer, format="png", engine="kaleido")
        buffer.seek(0)
        return buffer

    async def chart_earnings(self, ctx, member: Member, timeframe: str = "24h", interaction: Optional[discord.Interaction] = None):
        """Generate and send earnings chart embed"""
        data = await self.get_user_data(member.id)
        if not data:
            return None

        try:
            chart_buffer = await self.generate_smooth_chart(member.id, timeframe)
            chart_file = File(chart_buffer, "chart.png")

            embed = Embed(
                title=f"{member.name}'s Statistics",
            )
            embed.set_image(url="attachment://chart.png")

            fields = [
                ("Total Earnings", self.format_currency(data['earnings'])),
                ("Recent Earnings", self.format_currency(data['hourly_earnings'])),
                ("Win Rate", self.get_win_rate(data['wins'], data['total'])),
                ("Wallet", self.format_currency(data['balance'])),
                ("Bank", self.format_currency(data['bank'])),
                ("24h Earnings", self.format_currency(data['daily_earnings']))
            ]

            for name, value in fields:
                embed.add_field(name=name, value=value, inline=True)

            view = TimeframeView(self, ctx, member)
            
            if interaction:
                await interaction.message.edit(embed=embed, attachments=[chart_file], view=view)
            else:
                await ctx.send(embed=embed, file=chart_file, view=view)

        except Exception as e:
            await ctx.warn(f"Failed to generate chart: {str(e)}")
            return None

class TimeframeView(View):
    def __init__(self, chart_handler, ctx, member):
        super().__init__(timeout=60)
        self.chart = chart_handler
        self.ctx = ctx
        self.member = member

    async def on_timeout(self):
        """Disable buttons when view times out"""
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(view=self)
        except:
            pass

    @discord.ui.button(label="24H", style=ButtonStyle.secondary)
    async def hours_24(self, interaction: discord.Interaction, _):
        await interaction.response.defer()
        await self.chart.chart_earnings(self.ctx, self.member, timeframe="24h", interaction=interaction)

    @discord.ui.button(label="14D", style=ButtonStyle.secondary)
    async def days_14(self, interaction: discord.Interaction, _):
        await interaction.response.defer()
        await self.chart.chart_earnings(self.ctx, self.member, timeframe="14d", interaction=interaction)

    @discord.ui.button(label="30D", style=ButtonStyle.secondary)
    async def days_30(self, interaction: discord.Interaction, _):
        await interaction.response.defer()
        await self.chart.chart_earnings(self.ctx, self.member, timeframe="30d", interaction=interaction)