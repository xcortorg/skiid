from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os
from io import BytesIO
import aiohttp
from discord import File, Member
import numpy as np
from matplotlib.lines import Line2D
from scipy.interpolate import make_interp_spline

class InfoImageGenerator:
    def __init__(self):
        self.font_path = "assets/fonts/Montserrat-Bold.ttf" 
        self.background_color = '#09090B'
        self.card_color = '#111113'
        self.text_color = '#FFFFFF'
        self.accent_color = '#5C7CFA'
        self.muted_color = '#71717A'

    def draw_card(self, draw, x, y, width, height, radius=12):
        """Draw a rounded rectangle card"""
        draw.pieslice([x, y, x + radius * 2, y + radius * 2], 180, 270, fill=self.card_color)
        draw.pieslice([x + width - radius * 2, y, x + width, y + radius * 2], 270, 0, fill=self.card_color)
        draw.pieslice([x, y + height - radius * 2, x + radius * 2, y + height], 90, 180, fill=self.card_color)
        draw.pieslice([x + width - radius * 2, y + height - radius * 2, x + width, y + height], 0, 90, fill=self.card_color)
        
        draw.rectangle([x + radius, y, x + width - radius, y + height], fill=self.card_color)  # Vertical
        draw.rectangle([x, y + radius, x + width, y + height - radius], fill=self.card_color)  # Horizontal

    def create_activity_chart(self, stats, width=1060, height=180):
        plt.style.use('dark_background')
        fig = plt.figure(figsize=(width/80, height/80))
        ax = fig.add_subplot(111)
        
        messages_data = [float(x or 0) for x in stats.get('messages_7d_series', [0] * 7)]
        voice_data = [float(x or 0) for x in stats.get('voice_7d_series', [0] * 7)]
        
        max_messages = max(messages_data) if max(messages_data) > 0 else 1
        voice_data = [x * (max_messages / max(voice_data) if max(voice_data) > 0 else 1) * 0.8 for x in voice_data]
        
        days = [(datetime.now() - timedelta(days=i)).strftime('%d/%m') for i in range(6, -1, -1)]
        x = np.array(range(len(days)))
        
        x_smooth = np.linspace(x.min(), x.max(), 200)
        
        messages_spline = make_interp_spline(x, messages_data, k=2)
        voice_spline = make_interp_spline(x, voice_data, k=2)
        
        messages_smooth = messages_spline(x_smooth)
        voice_smooth = voice_spline(x_smooth)
        
        messages_smooth = np.maximum(messages_smooth, 0)
        voice_smooth = np.maximum(voice_smooth, 0)
        
        ax.set_xlim(-0.3, len(days) - 0.7)
        ax.set_ylim(0, max(max(messages_smooth), max(voice_smooth)) * 1.15)
        
        ax.plot(x_smooth, messages_smooth, color='#5C7CFA', linewidth=2.5, label='Messages')
        ax.plot(x_smooth, voice_smooth, color='#10B981', linewidth=2.5, label='Voice Hours')
        
        ax.scatter(x, messages_data, color='#5C7CFA', s=35, zorder=5)
        ax.scatter(x, voice_data, color='#10B981', s=35, zorder=5)
        
        ax.fill_between(x_smooth, messages_smooth, alpha=0.1, color='#5C7CFA')
        ax.fill_between(x_smooth, voice_smooth, alpha=0.1, color='#10B981')
        
        ax.set_xticks(x)
        ax.set_xticklabels(days, color='#A1A1AA', fontsize=8)
        ax.grid(True, color='#27272A', alpha=0.2)
        
        ax.set_facecolor('#111113')
        fig.patch.set_facecolor('#111113')
        
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
        
        ax.legend(loc='lower right', frameon=False, labelcolor='#A1A1AA', fontsize=8)
        
        plt.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.02)
        
        buffer = BytesIO()
        plt.savefig(buffer, format='png', transparent=True, dpi=100, bbox_inches='tight', pad_inches=0.1)
        buffer.seek(0)
        chart_image = Image.open(buffer)
        plt.close()
        
        chart_image = chart_image.resize((1100, 180), Image.Resampling.LANCZOS)
        
        return chart_image

    async def generate_server_info(self, guild, stats, top_stats=None):
        image = Image.new('RGB', (1200, 940), self.background_color)
        draw = ImageDraw.Draw(image)
        
        self.draw_card(draw, 40, 20, 400, 100)  
        self.draw_card(draw, 460, 20, 340, 100) 
        self.draw_card(draw, 820, 20, 340, 100) 
        
        self.draw_card(draw, 40, 135, 540, 160) 
        self.draw_card(draw, 600, 135, 560, 160) 
        
        self.draw_card(draw, 60, 195, 150, 80)  
        self.draw_card(draw, 240, 195, 150, 80) 
        self.draw_card(draw, 420, 195, 150, 80)  
        
        self.draw_card(draw, 620, 195, 150, 80) 
        self.draw_card(draw, 800, 195, 150, 80)  
        self.draw_card(draw, 980, 195, 150, 80)  
        
        self.draw_card(draw, 40, 310, 540, 300) 
        self.draw_card(draw, 600, 310, 560, 300) 
        
        self.draw_card(draw, 40, 625, 1120, 260) 

        title_font = ImageFont.truetype(self.font_path, 42)
        header_font = ImageFont.truetype(self.font_path, 28)
        text_font = ImageFont.truetype(self.font_path, 22)
        period_font = ImageFont.truetype(self.font_path, 24)
        stats_font = ImageFont.truetype(self.font_path, 26)

        if guild.icon:
            async with aiohttp.ClientSession() as session:
                async with session.get(str(guild.icon.url)) as resp:
                    if resp.status == 200:
                        icon_data = await resp.read()
                        icon = Image.open(BytesIO(icon_data))
                        icon = icon.resize((80, 80))
                        mask = Image.new('L', icon.size, 0)
                        mask_draw = ImageDraw.Draw(mask)
                        mask_draw.ellipse((0, 0, 80, 80), fill=255)
                        image.paste(icon, (60, 30), mask)

        def truncate_text(text, font, max_width):
            width = draw.textlength(text, font=font)
            if width <= max_width:
                return text
            
            while width > max_width and len(text) > 0:
                text = text[:-1]
                width = draw.textlength(text + "...", font=font)
            return text + "..."

        guild_name = truncate_text(guild.name, title_font, 280)
        draw.text((160, 35), guild_name, self.text_color, font=title_font)
        draw.text((160, 85), "Server Statistics", self.muted_color, font=text_font)
        
        draw.text((480, 35), "Created", self.text_color, font=header_font)
        created_date = guild.created_at.strftime('%B %d, %Y')
        created_width = draw.textlength(created_date, font=text_font)
        draw.text((480, 70), created_date, self.accent_color, font=text_font)
        
        draw.text((840, 35), "Bot Added", self.text_color, font=header_font)
        bot_added = guild.me.joined_at if guild.me else datetime.now()
        bot_date = bot_added.strftime('%B %d, %Y')
        bot_width = draw.textlength(bot_date, font=text_font)
        draw.text((840, 70), bot_date, self.accent_color, font=text_font)
        
        draw.text((60, 145), "Messages", self.text_color, font=header_font)
        x_positions = [80, 260, 440]
        periods = ['1d', '7d', '14d']
        for i, (x, period) in enumerate(zip(x_positions, periods)):
            draw.text((x, 200), period, self.accent_color, font=period_font)
            messages = f"{stats.get(f'messages_{period}', 0):,}"
            draw.text((x, 230), messages, self.text_color, font=stats_font)

        draw.text((620, 145), "Voice Activity", self.text_color, font=header_font)
        x_positions = [640, 820, 1000]
        for i, (x, period) in enumerate(zip(x_positions, periods)):
            draw.text((x, 200), period, self.accent_color, font=period_font)
            hours = f"{stats.get(f'voice_{period}', 0):.1f}h"
            draw.text((x, 230), hours, self.text_color, font=stats_font)

        draw.text((60, 325), "Top Members", self.text_color, font=header_font)
        y = 370
        
        members_data = top_stats.get('members', [])
        while len(members_data) < 3:
            members_data.append({'member_id': None, 'total': 0})
        
        for member_data in members_data[:3]:
            self.draw_card(draw, 60, y, 500, 70)
            if member_data['member_id']:
                member = guild.get_member(member_data['member_id'])
                name = member.display_name if member else str(member_data['member_id'])
                msg_count = f"{member_data['total']:,} messages"
            else:
                name = "No activity"
                msg_count = "0 messages"
                
            draw.text((80, y + 10), name, self.text_color, font=text_font)
            draw.text((80, y + 35), msg_count, self.accent_color, font=text_font)
            y += 80

        draw.text((620, 325), "Top Channels", self.text_color, font=header_font)
        y = 370
        
        channels_data = top_stats.get('channels', [])
        while len(channels_data) < 3:
            channels_data.append({'channel_id': None, 'total': 0})
            
        for channel in channels_data[:3]:
            self.draw_card(draw, 620, y, 520, 70)
            if channel['channel_id']:
                channel_obj = guild.get_channel(channel['channel_id'])
                name = channel_obj.name if channel_obj else 'Unknown'
                msg_count = f"{channel['total']:,} messages"
            else:
                name = "No activity"
                msg_count = "0 messages"
                
            draw.text((640, y + 10), f"#{name}", self.text_color, font=text_font)
            draw.text((640, y + 35), msg_count, self.accent_color, font=text_font)
            y += 80

        draw.text((60, 640), "Activity Overview", self.text_color, font=header_font)
        chart = self.create_activity_chart(stats)
        image.paste(chart, (60, 680), chart if chart.mode == 'RGBA' else None)

        powered_font = ImageFont.truetype(self.font_path, 18)
        powered_text = "Powered by Evict"
        text_width = int(draw.textlength(powered_text, font=powered_font))
        
        async with aiohttp.ClientSession() as session:
            async with session.get("https://r2.evict.bot/evict-new.png") as resp:
                if resp.status == 200:
                    logo_data = await resp.read()
                    logo = Image.open(BytesIO(logo_data))
                    logo = logo.resize((24, 24))
                    logo_x = int(1160 - text_width - 30)
                    image.paste(logo, (logo_x, 903), logo if logo.mode == 'RGBA' else None)
                    draw.text((1160 - text_width, 905), powered_text, self.muted_color, font=powered_font)

        buffer = BytesIO()
        image.save(buffer, 'PNG')
        buffer.seek(0)
        return File(buffer, 'server_info.png')

    async def generate_user_info(self, guild, user, stats):
        image = Image.new('RGB', (1200, 940), self.background_color)
        draw = ImageDraw.Draw(image)
        
        self.draw_card(draw, 40, 20, 400, 100)  
        self.draw_card(draw, 460, 20, 340, 100) 
        self.draw_card(draw, 820, 20, 340, 100) 
        
        self.draw_card(draw, 40, 135, 540, 160) 
        self.draw_card(draw, 600, 135, 560, 160)  
        
        self.draw_card(draw, 60, 195, 150, 80)
        self.draw_card(draw, 240, 195, 150, 80)
        self.draw_card(draw, 420, 195, 150, 80)
        
        self.draw_card(draw, 620, 195, 150, 80)
        self.draw_card(draw, 800, 195, 150, 80)
        self.draw_card(draw, 980, 195, 150, 80)
        
        self.draw_card(draw, 40, 310, 540, 300)  
        self.draw_card(draw, 600, 310, 560, 300)
        
        self.draw_card(draw, 40, 625, 1120, 260)

        title_font = ImageFont.truetype(self.font_path, 42)
        header_font = ImageFont.truetype(self.font_path, 28)
        text_font = ImageFont.truetype(self.font_path, 22)
        period_font = ImageFont.truetype(self.font_path, 24)
        stats_font = ImageFont.truetype(self.font_path, 26)

        if user.avatar:
            async with aiohttp.ClientSession() as session:
                async with session.get(str(user.avatar.url)) as resp:
                    if resp.status == 200:
                        avatar_data = await resp.read()
                        avatar = Image.open(BytesIO(avatar_data))
                        avatar = avatar.resize((80, 80))
                        mask = Image.new('L', avatar.size, 0)
                        mask_draw = ImageDraw.Draw(mask)
                        mask_draw.ellipse((0, 0, 80, 80), fill=255)
                        image.paste(avatar, (60, 30), mask)

        draw.text((160, 35), user.name, self.text_color, font=title_font)
        draw.text((160, 85), user.display_name, self.muted_color, font=text_font)
        
        draw.text((480, 35), "Created", self.text_color, font=header_font)
        created_date = user.created_at.strftime('%B %d, %Y')
        draw.text((480, 70), created_date, self.accent_color, font=text_font)
        
        draw.text((840, 35), "Joined", self.text_color, font=header_font)
        joined_date = user.joined_at.strftime('%B %d, %Y')
        draw.text((840, 70), joined_date, self.accent_color, font=text_font)

        draw.text((60, 145), "Message Stats", self.text_color, font=header_font)
        periods = [('1d', '1d'), ('7d', '7d'), ('14d', '14d')]
        for i, (period, display) in enumerate(periods):
            x_pos = 60 + (i * 180)
            
            self.draw_card(draw, x_pos, 195, 150, 80)
            
            past_text = f"Past {display}"
            past_width = draw.textlength(past_text, font=text_font)
            past_x = x_pos + (150 - past_width) // 2
            draw.text((past_x, 205), past_text, self.text_color, font=text_font)
            
            value = str(stats['messages'][period])
            value_width = draw.textlength(value, font=stats_font)
            value_x = x_pos + (150 - value_width) // 2
            draw.text((value_x, 235), value, self.accent_color, font=stats_font)

        draw.text((620, 145), "Voice Stats", self.text_color, font=header_font)
        for i, (period, display) in enumerate(periods):
            x_pos = 620 + (i * 180)
            
            self.draw_card(draw, x_pos, 195, 150, 80)
            
            past_text = f"Past {display}"
            past_width = draw.textlength(past_text, font=text_font)
            past_x = x_pos + (150 - past_width) // 2
            draw.text((past_x, 205), past_text, self.text_color, font=text_font)
            
            value = f"{stats['voice'][period]:.1f}h"
            value_width = draw.textlength(value, font=stats_font)
            value_x = x_pos + (150 - value_width) // 2
            draw.text((value_x, 235), value, self.accent_color, font=stats_font)

        draw.text((60, 325), "Message Activity", self.text_color, font=header_font)
        for i, (period, display) in enumerate(periods):
            y_pos = 370 + (i * 57)
            self.draw_card(draw, 60, y_pos, 500, 55)
            
            draw.text((80, y_pos + 15), f"Past {display}:", self.text_color, font=text_font)
            
            messages = f"{stats['messages'][period]} messages"
            messages_width = draw.textlength(messages, font=text_font)
            draw.text((400, y_pos + 15), messages, self.accent_color, font=text_font)

        draw.text((620, 325), "Voice Activity", self.text_color, font=header_font)
        for i, (period, display) in enumerate(periods):
            y_pos = 370 + (i * 57)
            self.draw_card(draw, 620, y_pos, 520, 55)
            
            draw.text((640, y_pos + 15), f"Past {display}:", self.text_color, font=text_font)
            
            hours = f"{stats['voice'][period]:.1f} hours"
            hours_width = draw.textlength(hours, font=text_font)
            draw.text((980, y_pos + 15), hours, self.accent_color, font=text_font)

        draw.text((60, 640), "Activity Overview", self.text_color, font=header_font)
        chart = self.create_activity_chart({
            'messages_7d_series': stats['activity']['messages_series'],
            'voice_7d_series': stats['activity']['voice_series']
        })
        image.paste(chart, (60, 680), chart if chart.mode == 'RGBA' else None)

        powered_font = ImageFont.truetype(self.font_path, 18)
        powered_text = "Powered by Evict"
        text_width = int(draw.textlength(powered_text, font=powered_font))
        
        async with aiohttp.ClientSession() as session:
            async with session.get("https://r2.evict.bot/evict-new.png") as resp:
                if resp.status == 200:
                    logo_data = await resp.read()
                    logo = Image.open(BytesIO(logo_data))
                    logo = logo.resize((24, 24))
                    logo_x = int(1160 - text_width - 30)
                    image.paste(logo, (logo_x, 903), logo if logo.mode == 'RGBA' else None)
                    draw.text((1160 - text_width, 905), powered_text, self.muted_color, font=powered_font)

        buffer = BytesIO()
        image.save(buffer, 'PNG')
        buffer.seek(0)
        return File(buffer, 'user_info.png')

    def create_detailed_chart(self, stats, width=1060, height=350):
        plt.style.use('dark_background')
        fig = plt.figure(figsize=(width/100, height/100))
        ax = fig.add_subplot(111)
        
        data = [float(x or 0) for x in stats['series']]
        days = [(datetime.now() - timedelta(days=i)).strftime('%d/%m') for i in range(6, -1, -1)]
        x = np.array(range(len(days)))
        
        x_smooth = np.linspace(x.min(), x.max(), 200)
        spline = make_interp_spline(x, data, k=2)
        smooth_data = spline(x_smooth)
        smooth_data = np.maximum(smooth_data, 0)
        
        ax.set_xlim(-0.2, len(days) - 0.8)
        max_val = max(smooth_data) if max(smooth_data) > 0 else 1
        ax.set_ylim(0, max_val * 1.1)
        
        yticks = np.linspace(0, max_val, 6)
        ax.set_yticks(yticks)
        ax.set_yticklabels([f'{int(y):,}' for y in yticks], color='#71717A', fontsize=8)
        
        ax.plot(x_smooth, smooth_data, color=self.accent_color, linewidth=2.5)
        ax.scatter(x, data, color=self.accent_color, s=35, zorder=5)
        ax.fill_between(x_smooth, smooth_data, alpha=0.1, color=self.accent_color)
        
        ax.set_xticks(x)
        ax.set_xticklabels(days, color='#71717A', fontsize=8)
        ax.grid(True, color='#27272A', alpha=0.2)
        
        ax.set_facecolor(self.card_color)
        fig.patch.set_facecolor(self.card_color)
        
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.spines['left'].set_visible(True)
        ax.spines['left'].set_color('#27272A')
        
        plt.tight_layout(pad=0.5)
        
        buffer = BytesIO()
        plt.savefig(buffer, format='png', transparent=True, dpi=100, bbox_inches='tight', pad_inches=0.1)
        buffer.seek(0)
        chart_image = Image.open(buffer)
        plt.close()
        
        return chart_image

    async def generate_chart(self, stats):
        image = Image.new('RGB', (1200, 650), self.background_color)  
        draw = ImageDraw.Draw(image)

        title_font = ImageFont.truetype(self.font_path, 42)
        header_font = ImageFont.truetype(self.font_path, 28)
        text_font = ImageFont.truetype(self.font_path, 22)
        stats_font = ImageFont.truetype(self.font_path, 16)

        self.draw_card(draw, 40, 20, 400, 100)  
        self.draw_card(draw, 460, 20, 340, 100) 
        self.draw_card(draw, 820, 20, 340, 100)  

        y_pos = 140
        self.draw_card(draw, 40, y_pos, 1120, 460)

        if guild_icon := stats.get('guild_icon'):
            async with aiohttp.ClientSession() as session:
                async with session.get(str(guild_icon.url)) as resp:
                    if resp.status == 200:
                        icon_data = await resp.read()
                        icon = Image.open(BytesIO(icon_data))
                        icon = icon.resize((80, 80))
                        mask = Image.new('L', icon.size, 0)
                        mask_draw = ImageDraw.Draw(mask)
                        mask_draw.ellipse((0, 0, 80, 80), fill=255)
                        image.paste(icon, (60, 30), mask)

        guild_name = stats.get('guild_name', 'Server')
        guild_name = self.truncate_text(guild_name, title_font, 280)
        draw.text((160, 35), guild_name, self.text_color, font=title_font)
        draw.text((160, 85), "Server Statistics", self.muted_color, font=text_font)

        draw.text((480, 35), "Created", self.text_color, font=header_font)
        created_date = stats.get('created_at', 'Unknown').strftime('%B %d, %Y')
        draw.text((480, 75), created_date, self.accent_color, font=text_font)

        draw.text((840, 35), "Members", self.text_color, font=header_font)
        member_count = str(stats.get('member_count', 0))
        draw.text((840, 75), member_count, self.accent_color, font=text_font)

        draw.text((60, y_pos + 15), 
                 "Message Activity" if stats['type'] == 'messages' else "Voice Activity", 
                 self.text_color, font=header_font)

        if stats['type'] == 'messages':
            total_messages = stats.get('total_messages', 0)
            
            self.draw_card(draw, 860, y_pos + 15, 180, 35)
            self.draw_card(draw, 1050, y_pos + 15, 90, 35)
            
            messages_text = "Messages:"
            messages_value = f"{int(total_messages):,}"
            messages_label_width = int(draw.textlength(messages_text, font=stats_font))
            
            draw.text((870, y_pos + 25), messages_text, self.muted_color, font=stats_font)
            draw.text((870 + messages_label_width + 5, y_pos + 25), messages_value, self.accent_color, font=stats_font)
            
            active_text = "Active:"
            active_value = str(stats.get('active_members', 0))
            active_label_width = int(draw.textlength(active_text, font=stats_font))
            draw.text((1060, y_pos + 25), active_text, self.muted_color, font=stats_font)
            draw.text((1060 + active_label_width + 5, y_pos + 25), active_value, self.accent_color, font=stats_font)
        elif stats['type'] == 'voice':
            total_hours = sum(stats['series'])
            
            self.draw_card(draw, 860, y_pos + 15, 180, 35) 
            self.draw_card(draw, 1050, y_pos + 15, 90, 35) 
            
            hours_text = "Hours:"
            hours_value = f"{total_hours:.1f}"
            hours_label_width = int(draw.textlength(hours_text, font=stats_font))
            
            draw.text((870, y_pos + 25), hours_text, self.muted_color, font=stats_font)
            draw.text((870 + hours_label_width + 5, y_pos + 25), hours_value, self.accent_color, font=stats_font)
            
            active_text = "Active:"
            active_value = str(stats.get('active_members', 0))
            active_label_width = int(draw.textlength(active_text, font=stats_font))
            draw.text((1060, y_pos + 25), active_text, self.muted_color, font=stats_font)
            draw.text((1060 + active_label_width + 5, y_pos + 25), active_value, self.accent_color, font=stats_font)

        chart = self.create_detailed_chart(stats, width=1060, height=350)
        image.paste(chart, (60, y_pos + 60), chart if chart.mode == 'RGBA' else None)

        powered_font = ImageFont.truetype(self.font_path, 18)
        powered_text = "Powered by Evict"
        text_width = int(draw.textlength(powered_text, font=powered_font))
        
        async with aiohttp.ClientSession() as session:
            async with session.get("https://r2.evict.bot/evict-new.png") as resp:
                if resp.status == 200:
                    logo_data = await resp.read()
                    logo = Image.open(BytesIO(logo_data))
                    logo = logo.resize((24, 24))
                    logo_x = int(1160 - text_width - 30)
                    image.paste(logo, (logo_x, 613), logo if logo.mode == 'RGBA' else None)
                    draw.text((1160 - text_width, 615), powered_text, self.muted_color, font=powered_font)

        buffer = BytesIO()
        image.save(buffer, 'PNG')
        buffer.seek(0)
        return File(buffer, 'activity_chart.png')

    def truncate_text(self, text, font, max_width):
        draw = ImageDraw.Draw(Image.new('RGB', (1, 1)))
        width = draw.textlength(text, font=font)
        if width <= max_width:
            return text
        
        while width > max_width and len(text) > 0:
            text = text[:-1]
            width = draw.textlength(text + "...", font=font)
        return text + "..."