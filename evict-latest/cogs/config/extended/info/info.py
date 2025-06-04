from discord.ext.commands import Cog, group
from discord import Embed, Message, Member
from core.client.context import Context
from tools import CompositeMetaClass, MixinMeta
from humanfriendly import format_timespan
from .image import InfoImageGenerator
from discord.ui import View, Button
import discord 
from datetime import datetime

class Info(MixinMeta, metaclass=CompositeMetaClass):
    """
    View server information and statistics.
    """
    async def generate_image(self, guild, stats, top_stats=None):
        """Generate and return server info image"""
        image_generator = InfoImageGenerator()
        return await image_generator.generate_server_info(guild, stats, top_stats)

    @group(invoke_without_command=True)
    async def info(self, ctx: Context) -> Message:
        """View server information."""
        
        stats = await self.bot.db.fetchrow(
            """
            WITH daily_messages AS (
                SELECT 
                    date_trunc('day', date)::date as day,
                    SUM(messages_sent) as messages,
                    SUM(voice_minutes)/60.0 as voice_hours
                FROM statistics.daily 
                WHERE guild_id = $1
                AND date > CURRENT_DATE - INTERVAL '7 days'
                GROUP BY day
                ORDER BY day
            ),
            today AS (
                SELECT 
                    CURRENT_DATE as day,
                    SUM(messages_sent) as messages,
                    SUM(voice_minutes)/60.0 as voice_hours
                FROM statistics.daily
                WHERE guild_id = $1
                AND date >= CURRENT_DATE
                GROUP BY CURRENT_DATE
            ),
            all_days AS (
                SELECT generate_series(
                    CURRENT_DATE - INTERVAL '6 days',
                    CURRENT_DATE,
                    '1 day'::interval
                )::date as day
            ),
            filled_days AS (
                SELECT 
                    ad.day,
                    COALESCE(dm.messages, 0) as messages,
                    COALESCE(dm.voice_hours, 0) as voice_hours
                FROM all_days ad
                LEFT JOIN daily_messages dm ON dm.day = ad.day
                ORDER BY ad.day
            )
            SELECT 
                (SELECT messages FROM today) as messages_1d,
                (SELECT SUM(messages) FROM filled_days) as messages_7d,
                (SELECT SUM(messages) FROM filled_days) as messages_14d,
                (SELECT voice_hours FROM today) as voice_1d,
                (SELECT SUM(voice_hours) FROM filled_days) as voice_7d,
                (SELECT SUM(voice_hours) FROM filled_days) as voice_14d,
                (SELECT array_agg(messages ORDER BY day) FROM filled_days) as messages_7d_series,
                (SELECT array_agg(voice_hours ORDER BY day) FROM filled_days) as voice_7d_series
            """,
            ctx.guild.id
        )

        top_stats = {
            'members': await self.bot.db.fetch(
                """
                SELECT 
                    member_id,
                    SUM(messages_sent) as total
                FROM statistics.daily
                WHERE guild_id = $1
                AND date >= CURRENT_DATE - INTERVAL '7 days'
                GROUP BY member_id
                ORDER BY total DESC
                LIMIT 3
                """,
                ctx.guild.id
            ),
            'channels': await self.bot.db.fetch(
                """
                SELECT 
                    channel_id,
                    SUM(messages_sent) as total
                FROM statistics.daily_channels
                WHERE guild_id = $1
                AND date >= CURRENT_DATE - INTERVAL '7 days'
                GROUP BY channel_id
                ORDER BY total DESC
                LIMIT 3
                """,
                ctx.guild.id
            )
        }

        image = await self.generate_image(ctx.guild, stats, top_stats)
        return await ctx.send(file=image)

    @info.command(name="voice")
    async def info_voice(self, ctx: Context) -> Message:
        """View voice activity information."""
        
        voice_stats = await self.bot.db.fetchrow(
            """
            SELECT SUM(voice_minutes) as total_voice
            FROM statistics.daily 
            WHERE guild_id = $1
            """,
            ctx.guild.id
        )

        embed = Embed(
            title=f"🎤 Voice Activity in {ctx.guild.name}",
            color=ctx.color
        )
        
        if voice_stats and voice_stats['total_voice']:
            voice_mins = voice_stats['total_voice']
            embed.description = f"Total voice time: `{format_timespan(voice_mins * 60)}`"
        else:
            embed.description = "No voice activity recorded yet"

        voice_channels = [vc for vc in ctx.guild.voice_channels if len(vc.members) > 0]
        if voice_channels:
            embed.add_field(
                name="Currently Active",
                value="\n".join(
                    f"• {vc.name}: `{len(vc.members)}` members"
                    for vc in voice_channels
                ),
                inline=False
            )

        return await ctx.send(embed=embed)

    @info.command(name="messages")
    async def info_messages(self, ctx: Context) -> Message:
        """View message activity information."""
        
        msg_stats = await self.bot.db.fetchrow(
            """
            SELECT SUM(messages_sent) as total_messages
            FROM statistics.daily 
            WHERE guild_id = $1
            """,
            ctx.guild.id
        )

        embed = Embed(
            title=f"💬 Message Activity in {ctx.guild.name}",
            color=ctx.color
        )
        
        if msg_stats and msg_stats['total_messages']:
            messages = msg_stats['total_messages']
            embed.description = f"Total messages sent: `{messages:,}`"
        else:
            embed.description = "No message activity recorded yet"

        return await ctx.send(embed=embed)

    @info.command(name="daily")
    async def info_daily(self, ctx: Context) -> Message:
        """View daily statistics for the past 7 days."""
        
        daily_stats = await self.bot.db.fetch(
            """
            SELECT 
                date,
                messages_sent,
                voice_minutes/60.0 as voice_hours
            FROM statistics.daily 
            WHERE guild_id = $1
            AND date > CURRENT_DATE - INTERVAL '7 days'
            ORDER BY date DESC
            """,
            ctx.guild.id
        )

        embed = Embed(
            title=f"📊 Daily Activity in {ctx.guild.name}",
            description="Statistics for the past 7 days",
            color=ctx.color
        )
        
        if daily_stats:
            for stat in daily_stats:
                date = stat['date'].strftime("%Y-%m-%d")
                messages = f"{stat['messages_sent']:,}" if stat['messages_sent'] else "0"
                voice = f"{stat['voice_hours']:.1f}" if stat['voice_hours'] else "0.0"
                
                embed.add_field(
                    name=date,
                    value=f"Messages: `{messages}`\nVoice Hours: `{voice}`",
                    inline=False
                )
        else:
            embed.description = "No activity recorded in the past 7 days"

        return await ctx.send(embed=embed)

    @info.command(name="user", example="x")
    async def info_user(self, ctx: Context, user: Member = None) -> Message:
        """View user statistics and activity."""
        user = user or ctx.author
        
        ranks = await self.bot.db.fetch(
            """
            WITH member_stats AS (
                SELECT 
                    unnest(member_ids) as member_id,
                    SUM(messages_sent) as messages,
                    SUM(voice_minutes)/60.0 as voice_hours
                FROM statistics.daily 
                WHERE guild_id = $1
                AND date >= CURRENT_DATE - INTERVAL '7 days'
                GROUP BY unnest(member_ids)
            ),
            message_ranks AS (
                SELECT 
                    member_id,
                    messages,
                    RANK() OVER (ORDER BY messages DESC) as msg_rank
                FROM member_stats
            ),
            voice_ranks AS (
                SELECT 
                    member_id,
                    voice_hours,
                    RANK() OVER (ORDER BY voice_hours DESC) as voice_rank
                FROM member_stats
            )
            SELECT 
                m.msg_rank,
                v.voice_rank
            FROM message_ranks m
            FULL OUTER JOIN voice_ranks v ON m.member_id = v.member_id
            WHERE m.member_id = $2 OR v.member_id = $2
            """,
            ctx.guild.id,
            user.id
        )

        message_rank = f"#{ranks[0]['msg_rank']}" if ranks and ranks[0]['msg_rank'] else "N/A"
        voice_rank = f"#{ranks[0]['voice_rank']}" if ranks and ranks[0]['voice_rank'] else "N/A"

        stats = await self.bot.db.fetchrow(
            """
            WITH daily_messages AS (
                SELECT 
                    date_trunc('day', date)::date as day,
                    SUM(messages_sent) as messages,
                    SUM(voice_minutes)/60.0 as voice_hours
                FROM statistics.daily 
                WHERE guild_id = $1
                AND $2 = ANY(member_ids)
                AND date > CURRENT_DATE - INTERVAL '14 days'
                GROUP BY day
                ORDER BY day
            ),
            today AS (
                SELECT 
                    CURRENT_DATE as day,
                    SUM(messages_sent) as messages,
                    SUM(voice_minutes)/60.0 as voice_hours
                FROM statistics.daily
                WHERE guild_id = $1
                AND $2 = ANY(member_ids)
                AND date >= CURRENT_DATE
                GROUP BY CURRENT_DATE
            ),
            all_days AS (
                SELECT generate_series(
                    CURRENT_DATE - INTERVAL '6 days',
                    CURRENT_DATE,
                    '1 day'::interval
                )::date as day
            ),
            filled_days AS (
                SELECT 
                    ad.day,
                    COALESCE(dm.messages, 0) as messages,
                    COALESCE(dm.voice_hours, 0) as voice_hours
                FROM all_days ad
                LEFT JOIN daily_messages dm ON dm.day = ad.day
                ORDER BY ad.day
            )
            SELECT 
                (SELECT messages FROM today) as messages_1d,
                (SELECT SUM(messages) FROM filled_days) as messages_7d,
                (SELECT SUM(messages) FROM daily_messages) as messages_14d,
                (SELECT voice_hours FROM today) as voice_1d,
                (SELECT SUM(voice_hours) FROM filled_days) as voice_7d,
                (SELECT SUM(voice_hours) FROM daily_messages) as voice_14d,
                (SELECT array_agg(messages ORDER BY day) FROM filled_days) as messages_7d_series,
                (SELECT array_agg(voice_hours ORDER BY day) FROM filled_days) as voice_7d_series
            """,
            ctx.guild.id,
            user.id
        )

        channels = await self.bot.db.fetch(
            """
            SELECT 
                channel_id,
                SUM(messages_sent) as total
            FROM statistics.daily_channels
            WHERE guild_id = $1
            AND date >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY channel_id
            ORDER BY total DESC
            LIMIT 2
            """,
            ctx.guild.id
        )

        image_generator = InfoImageGenerator()
        user_stats = {
            'ranks': {
                'message': message_rank,
                'voice': voice_rank
            },
            'messages': {
                '1d': stats['messages_1d'] or 0,
                '7d': stats['messages_7d'] or 0,
                '14d': stats['messages_14d'] or 0
            },
            'voice': {
                '1d': stats['voice_1d'] or 0,
                '7d': stats['voice_7d'] or 0,
                '14d': stats['voice_14d'] or 0
            },
            'channels': channels,
            'activity': {
                'messages_series': stats['messages_7d_series'],
                'voice_series': stats['voice_7d_series']
            }
        }

        image = await image_generator.generate_user_info(ctx.guild, user, user_stats)
        return await ctx.send(file=image)

    @info.group(name="chart")
    async def info_chart(self, ctx: Context):
        """View detailed activity charts"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @info_chart.command(name="messages")
    async def chart_messages(self, ctx: Context) -> Message:
        """View message activity charts"""
        stats = await self.bot.db.fetchrow(
            """
            WITH daily_stats AS (
                SELECT 
                    date_trunc('day', date)::date as day,
                    SUM(messages_sent) as messages
                FROM statistics.daily 
                WHERE guild_id = $1
                AND date > CURRENT_DATE - INTERVAL '7 days'
                GROUP BY day
                ORDER BY day
            ),
            member_counts AS (
                SELECT COUNT(DISTINCT member_id) as active_members,
                       SUM(messages_sent) as total_messages
                FROM statistics.daily
                WHERE guild_id = $1
                AND date > CURRENT_DATE - INTERVAL '7 days'
                AND messages_sent > 0
            ),
            filled_days AS (
                SELECT 
                    ad.day,
                    COALESCE(dm.messages, 0) as messages
                FROM (
                    SELECT generate_series(
                        CURRENT_DATE - INTERVAL '6 days',
                        CURRENT_DATE,
                        '1 day'::interval
                    )::date as day
                ) ad
                LEFT JOIN daily_stats dm ON dm.day = ad.day
                ORDER BY ad.day
            )
            SELECT 
                (SELECT array_agg(messages ORDER BY day) FROM filled_days) as messages_series,
                (SELECT array_agg(day::text ORDER BY day) FROM filled_days) as dates,
                (SELECT active_members FROM member_counts) as active_members,
                (SELECT total_messages FROM member_counts) as total_messages
            """,
            ctx.guild.id
        )

        chart_stats = {
            'type': 'messages',
            'series': stats['messages_series'],
            'dates': [datetime.strptime(d, '%Y-%m-%d') for d in stats['dates']],
            'guild_name': ctx.guild.name,
            'created_at': ctx.guild.created_at,
            'member_count': ctx.guild.member_count,
            'active_members': stats['active_members'],
            'total_messages': stats['total_messages'],
            'guild_icon': ctx.guild.icon
        }

        image_generator = InfoImageGenerator()
        image = await image_generator.generate_chart(chart_stats)
        view = ChartView(ctx, 'messages', stats)
        return await ctx.send(file=image, view=view)

    @info_chart.command(name="voice")
    async def chart_voice(self, ctx: Context) -> Message:
        """View voice activity charts"""
        stats = await self.bot.db.fetchrow(
            """
            WITH daily_stats AS (
                SELECT 
                    date_trunc('day', date)::date as day,
                    SUM(voice_minutes)/60.0 as voice_hours
                FROM statistics.daily 
                WHERE guild_id = $1
                AND date > CURRENT_DATE - INTERVAL '7 days'
                GROUP BY day
                ORDER BY day
            ),
            member_counts AS (
                SELECT COUNT(DISTINCT member_id) as active_members
                FROM statistics.daily
                WHERE guild_id = $1
                AND date > CURRENT_DATE - INTERVAL '7 days'
                AND voice_minutes > 0
            ),
            filled_days AS (
                SELECT 
                    ad.day,
                    COALESCE(dm.voice_hours, 0) as voice_hours
                FROM (
                    SELECT generate_series(
                        CURRENT_DATE - INTERVAL '6 days',
                        CURRENT_DATE,
                        '1 day'::interval
                    )::date as day
                ) ad
                LEFT JOIN daily_stats dm ON dm.day = ad.day
                ORDER BY ad.day
            )
            SELECT 
                (SELECT array_agg(voice_hours ORDER BY day) FROM filled_days) as voice_series,
                (SELECT array_agg(day::text ORDER BY day) FROM filled_days) as dates,
                (SELECT active_members FROM member_counts) as active_members
            """,
            ctx.guild.id
        )

        chart_stats = {
            'type': 'voice',
            'series': stats['voice_series'],
            'dates': [datetime.strptime(d, '%Y-%m-%d') for d in stats['dates']],
            'guild_name': ctx.guild.name,
            'created_at': ctx.guild.created_at,
            'member_count': ctx.guild.member_count,
            'active_members': stats['active_members'],
            'guild_icon': ctx.guild.icon
        }

        image_generator = InfoImageGenerator()
        image = await image_generator.generate_chart(chart_stats)
        view = ChartView(ctx, 'voice', stats)
        return await ctx.send(file=image, view=view)

class ChartView(View):
    def __init__(self, ctx, type, stats):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.type = type
        self.stats = stats
        self.detailed = False
        
        self.switch = Button(label="Show Details" if not self.detailed else "Show Chart", style=discord.ButtonStyle.gray)
        self.switch.callback = self.switch_view
        self.add_item(self.switch)
        
    async def switch_view(self, interaction: discord.Interaction):
        self.detailed = not self.detailed
        self.switch.label = "Show Details" if not self.detailed else "Show Chart"
        
        if self.detailed:
            embed = Embed(
                title=f"{'Message' if self.type == 'messages' else 'Voice'} Activity Details", 
                color=self.ctx.color
            )
            
            if self.type == 'messages':
                total = sum(self.stats['messages_series'])
                active = self.stats['active_members']
                embed.description = f"**Total Messages:** {int(total):,}\n**Active Members:** {active}"
            else:
                total = sum(self.stats['voice_series'])
                active = self.stats['active_members']
                embed.description = f"**Total Hours:** {total:.1f}\n**Active Members:** {active}"
            
            for day, value in zip(self.stats['dates'], self.stats[f'{self.type}_series']):
                date = datetime.strptime(day, '%Y-%m-%d')
                if self.type == 'messages':
                    embed.add_field(
                        name=date.strftime('%d/%m/%Y'),
                        value=f"{int(value):,} messages",
                        inline=True
                    )
                else:
                    embed.add_field(
                        name=date.strftime('%d/%m/%Y'),
                        value=f"{value:.1f} hours",
                        inline=True
                    )
            await interaction.response.edit_message(attachments=[], embed=embed, view=self)
        else:
            image_generator = InfoImageGenerator()
            chart_stats = {
                'type': self.type,
                'series': self.stats[f'{self.type}_series'],
                'dates': [datetime.strptime(d, '%Y-%m-%d') for d in self.stats['dates']],
                'guild_name': self.ctx.guild.name,
                'created_at': self.ctx.guild.created_at,
                'member_count': self.ctx.guild.member_count,
                'active_members': self.stats['active_members'],
                'guild_icon': self.ctx.guild.icon
            }
            
            if self.type == 'messages':
                chart_stats['total_messages'] = self.stats['total_messages']
            elif self.type == 'voice':
                chart_stats['total_hours'] = sum(self.stats['voice_series'])
                
            image = await image_generator.generate_chart(chart_stats)
            await interaction.response.edit_message(attachments=[image], embed=None, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.ctx.author.id