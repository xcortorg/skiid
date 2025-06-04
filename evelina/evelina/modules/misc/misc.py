import re
import io
import math
import urllib
import datetime
import discord
import asyncio
import requests
import colorgram
import humanfriendly
import concurrent.futures

from io import BytesIO
from PIL import Image, ImageOps, ImageFilter, ImageDraw, ImageFont, ImageSequence
from typing import Union
from datetime import datetime
from humanize import precisedelta

from discord import TextChannel, Role, VoiceChannel, Guild

from modules.styles import emojis

class Misc:
    def __init__(self, bot):
        self.bot = bot

    def humanize_number(self, number: float) -> str:
        try:
            n = float(number)
        except:
            return str(number)

        ip = f"{int(n):,}"
        if len(ip.replace(",", "")) <= 10:
            return f"{n:,.2f}"

        omitted = len(ip.replace(",", "")) - 10
        prefix = ip[:10]
        return f"{prefix}... (+{omitted})"

    def humanize_clean_number(self, number: float) -> str:
        try:
            n = float(number)
        except:
            return str(number)

        ip = f"{int(n):,}"
        if len(ip.replace(",", "")) <= 10:
            return ip

        omitted = len(ip.replace(",", "")) - 10
        prefix = ip[:10]
        return f"{prefix}... (+{omitted})"

    def humanize_date(self, date: datetime) -> str:
        if date.timestamp() < datetime.now().timestamp():
            return f"{(precisedelta(date, format='%0.0f').replace('and', ',')).split(', ')[0]} ago"
        else:
            return f"in {(precisedelta(date, format='%0.0f').replace('and', ',')).split(', ')[0]}"
    
    def humanize_time(self, seconds: int, minimalistic: bool = False, format: str = None) -> str:
            if format is None:
                time_string = humanfriendly.format_timespan(seconds, detailed=True)
                if minimalistic:
                    time_string = time_string.replace(" hours", "h").replace(" hour", "h")
                    time_string = time_string.replace(" minutes", "m").replace(" minute", "m")
                    time_string = time_string.replace(" seconds", "s").replace(" second", "s")
                return time_string
            hours, remainder = divmod(seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            time_parts = []
            if "HH" in format and hours > 0:
                time_parts.append(f"{hours:,}h" if minimalistic else f"{hours} hours")
            if "MM" in format and minutes > 0 or ("HH" in format and hours > 0):
                time_parts.append(f"{minutes:,}m" if minimalistic else f"{minutes} minutes")
            if "SS" in format and (seconds > 0 or ("MM" in format and minutes > 0) or ("HH" in format and hours > 0)):
                time_parts.append(f"{seconds:,}s" if minimalistic else f"{seconds} seconds")
            return " ".join(time_parts)

    def humanize_channel(self, channel_id: int, formated: bool = False):
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            return f"**{channel_id}**"
        if formated:
            return f"**{channel.mention}** (`{channel.id}`)"
        elif not formated:
            return f"{channel.mention}"

    def convert_channel(self, channel):
        if isinstance(channel, int):
            return channel
        elif isinstance(channel, TextChannel):
            return channel.id
        
    def humanize_voicechannel(self, channel_id: int, formated: bool = False):
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            return f"**{channel_id}**"
        if formated:
            return f"**{channel.mention}** (`{channel.id}`)"
        elif not formated:
            return f"{channel.mention}"
        
    def convert_voicechannel(self, channel):
        if isinstance(channel, int):
            return channel
        elif isinstance(channel, VoiceChannel):
            return channel.id
        
    def humanize_role(self, guild: Guild, role_id: int, formated: bool = False):
        role = guild.get_role(role_id)
        if role is None:
            return f"**{role_id}**"
        if formated:
            return f"**{role.mention}** (`{role.id}`)"
        elif not formated:
            return f"{role.mention}"
        
    def convert_role(self, role):
        if isinstance(role, int):
            return role
        elif isinstance(role, Role):
            return role.id
        
    async def dominant_color(self, url: Union[discord.Asset, str, None]) -> int:
        if isinstance(url, discord.Asset):
            url = url.url
        elif url is None:
            url = "http://cdn.discordapp.com/embed/avatars/1.png"
        try:
            img_data = await self.bot.session.get_bytes(url)
            img = Image.open(BytesIO(img_data))
            img.thumbnail((32, 32))
            colors = await asyncio.to_thread(lambda: colorgram.extract(img, 1))
            if not colors:
                raise ValueError("No colors found in the image.")
            dominant_color = discord.Color.from_rgb(*colors[0].rgb)
            return dominant_color.value
        except Exception as e:
            return discord.Color.from_rgb(114, 155, 176).value
        
    def url_encode(self, url: str):
        return urllib.parse.unquote(urllib.parse.quote_plus(url))
    
    async def get_badges(self, user):
        badges = []
        flags = user.public_flags
        if flags.staff:
            badges.append(f"{emojis.STAFF}")
        if flags.partner:
            badges.append(f"{emojis.PARTNER}")
        if flags.discord_certified_moderator:
            badges.append(f"{emojis.MOD}")
        if flags.hypesquad:
            badges.append(f"{emojis.HYPESQUAD}")
        if flags.hypesquad_bravery:
            badges.append(f"{emojis.BRAVERY}")
        if flags.hypesquad_brilliance:
            badges.append(f"{emojis.BRILLIANCE}")
        if flags.hypesquad_balance:
            badges.append(f"{emojis.BALANCE}")
        if flags.bug_hunter:
            badges.append(f"{emojis.BUGHUNTER1}")
        if flags.bug_hunter_level_2:
            badges.append(f"{emojis.BUGHUNTER2}")
        if flags.active_developer:
            badges.append(f"{emojis.ACTIVEDEVELOPER}")
        if flags.verified_bot_developer:
            badges.append(f"{emojis.BOTDEV}")
        if flags.early_supporter:
            badges.append(f"{emojis.EARLYSUPPORTER}")
        if user.avatar and user.avatar.is_animated():
            badges.append(f"{emojis.NITRO}")
        return " ".join(badges)
    
    def is_dangerous(self, role: discord.Role) -> bool:
        return any(
            [
                role.permissions.ban_members,
                role.permissions.kick_members,
                role.permissions.mention_everyone,
                role.permissions.manage_channels,
                role.permissions.manage_events,
                role.permissions.manage_expressions,
                role.permissions.manage_guild,
                role.permissions.manage_roles,
                role.permissions.manage_messages,
                role.permissions.manage_webhooks,
                role.permissions.manage_permissions,
                role.permissions.manage_threads,
                role.permissions.moderate_members,
                role.permissions.mute_members,
                role.permissions.deafen_members,
                role.permissions.move_members,
                role.permissions.administrator,
            ]
        )

    async def create_quote_image(self, avatar_url, text, bw, name):
        response = requests.get(avatar_url)
        avatar_image = Image.open(BytesIO(response.content)).resize((400, 400)).convert("RGBA")
        width, height = avatar_image.size
        avatar_image = avatar_image.crop((0, 0, width - 15, height))
        if bw:
            gray_avatar = ImageOps.grayscale(avatar_image)
            gray_avatar = gray_avatar.convert("RGBA")
            alpha = avatar_image.getchannel("A")
            gray_avatar.putalpha(alpha)
            avatar_image = gray_avatar
        fade = Image.new("L", avatar_image.size, 0)
        curve_intensity = 35 
        fade_length = int(avatar_image.width * 0.3)
        for y in range(fade.height):
            relative_y = (y / fade.height - 0.5) * 2
            curve_offset = int(curve_intensity * (1 - relative_y**2))
            for x in range(fade.width):
                base_x = x + curve_offset
                if base_x >= fade.width:
                    fade_value = 0
                else:
                    fade_value = int(255 * ((fade.width - base_x - 1) / fade.width))
                fade.putpixel((x, y), max(0, min(255, fade_value)))
        fade = fade.filter(ImageFilter.GaussianBlur(radius=2))
        avatar_with_fade = Image.composite(avatar_image, Image.new("RGBA", avatar_image.size, (0, 0, 0, 255)), fade)
        width, height = 800, 400
        base_image = Image.new("RGBA", (width, height), (0, 0, 0, 255))
        base_image.paste(avatar_with_fade, (0, 0), avatar_with_fade)
        quote_image = Image.new("RGBA", (width, height), (255, 255, 255, 0))
        draw = ImageDraw.Draw(quote_image)
        def wrap_text(text, font, max_width):
            lines = []
            words = text.split()
            line = ""
            for word in words:
                test_line = f"{line} {word}".strip()
                bbox = draw.textbbox((0, 0), test_line, font=font)
                text_width = bbox[2] - bbox[0]
                if text_width <= max_width:
                    line = test_line
                else:
                    lines.append(line)
                    line = word
            if line:
                lines.append(line)
            return lines
        font = ImageFont.truetype("data/fonts/ChocolatesBold.otf", 24)
        margin = 20
        max_width = width // 2 - 2 * margin
        emote_pattern = re.compile(r'<a?:(\w+):(\d+)>')
        mention_pattern = re.compile(r'<@!?(\d+)>')
        emote_size = 30
        def replace_emotes_and_mentions(text):
            emote_counter = 0
            mention_counter = 0
            emote_dict = {}
            mention_dict = {}
            def emote_replacer(match):
                nonlocal emote_counter
                emote_id = match.group(2)
                placeholder = f"__EMOTE_{emote_counter}__"
                emote_dict[placeholder] = emote_id
                emote_counter += 1
                return placeholder
            def mention_replacer(match):
                nonlocal mention_counter
                user_id = match.group(1)
                placeholder = f"__MENTION_{mention_counter}__"
                mention_dict[placeholder] = user_id
                mention_counter += 1
                return placeholder
            text = emote_pattern.sub(emote_replacer, text)
            text = mention_pattern.sub(mention_replacer, text)
            return text, emote_dict, mention_dict
        text, emote_dict, mention_dict = replace_emotes_and_mentions(text)
        wrapped_lines = wrap_text(text, font, max_width)
        y_text = (height - len(wrapped_lines) * 30) // 2
        left_shift = 50
        line_spacing = 10
        stripped_content = text.strip()
        non_emote_words = [word for word in re.split(r'(\s+|["“”])', stripped_content) if word.strip() and not emote_pattern.match(word)]
        only_emotes = len(non_emote_words) == 0
        contains_text_and_emote = bool(non_emote_words) and bool(emote_dict)
        for line in wrapped_lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            if only_emotes:
                text_x = width // 2 + 20 + (width // 2 - 20 - text_width) // 2
            else:
                text_x = width // 2 + 20 + (width // 2 - 20 - text_width) // 2 - left_shift
                if contains_text_and_emote:
                    text_x += 50
            words = re.split(r'(\s+)', line)
            x_offset = text_x
            for word in words:
                if word in emote_dict:
                    emote_id = emote_dict[word]
                    emote_url = f"https://cdn.discordapp.com/emojis/{emote_id}.png"
                    emote_response = requests.get(emote_url)
                    emote_image = Image.open(BytesIO(emote_response.content)).convert("RGBA")
                    emote_width, emote_height = emote_image.size
                    aspect_ratio = emote_height / emote_size
                    new_width = int(emote_width / aspect_ratio)
                    emote_image = emote_image.resize((new_width, emote_size))
                    quote_image.paste(emote_image, (x_offset, y_text - 10), emote_image)
                    x_offset += new_width
                elif word in mention_dict:
                    user_id = mention_dict[word]
                    mention_user = await self.bot.fetch_user(user_id)
                    mention_text = f"@{mention_user}"
                    draw.text((x_offset, y_text), mention_text, fill="white", font=font)
                    bbox = draw.textbbox((x_offset, y_text), mention_text, font=font)
                    mention_width = bbox[2] - bbox[0]
                    x_offset += mention_width
                else:
                    draw.text((x_offset, y_text), word, fill="white", font=font)
                    bbox = draw.textbbox((x_offset, y_text), word, font=font)
                    word_width = bbox[2] - bbox[0]
                    x_offset += word_width
            y_text += text_height + line_spacing
        current_year = datetime.now().year
        user_handle = f"- {name}, {current_year}"
        user_font = ImageFont.truetype("data/fonts/ChocolatesBoldItalic.otf", 18)
        bbox = draw.textbbox((0, 0), user_handle, font=user_font)
        handle_width = bbox[2] - bbox[0]
        handle_x = width // 2 + 20 + (width // 2 - 20 - handle_width) // 2 - left_shift
        handle_y = y_text + (30 if only_emotes else 10)
        draw.text((handle_x, handle_y), user_handle, fill="white", font=user_font)
        watermark_text = "Evelina"
        watermark_font = ImageFont.truetype("data/fonts/ChocolatesBold.otf", 12)
        bbox = draw.textbbox((0, 0), watermark_text, font=watermark_font)
        watermark_width = bbox[2] - bbox[0]
        watermark_x = width - watermark_width - 10
        watermark_y = height - bbox[3] + bbox[1] - 10
        draw.text((watermark_x, watermark_y), watermark_text, fill="white", font=watermark_font)
        final_image = Image.alpha_composite(base_image, quote_image)
        image_binary = io.BytesIO()
        final_image.save(image_binary, "PNG")
        image_binary.seek(0)
        return image_binary
    
    async def create_collage(self, image_bytes_list, thumb_size=(350, 350), columns=5):
        if not isinstance(image_bytes_list, list):
            raise ValueError("Expected a list of image bytes.")
        if len(image_bytes_list) == 0:
            raise ValueError("The image bytes list is empty.")
        def process_image(image_bytes):
            img = Image.open(BytesIO(image_bytes))
            if img.format == 'GIF':
                img = next(ImageSequence.Iterator(img)).convert('RGBA')
            else:
                img = img.convert('RGBA')
            img = img.resize(thumb_size, Image.Resampling.LANCZOS)
            return img
        with concurrent.futures.ThreadPoolExecutor() as executor:
            images = list(executor.map(process_image, image_bytes_list))
        num_images = len(images)
        rows = math.ceil(num_images / columns)
        collage_width = thumb_size[0] * columns
        collage_height = thumb_size[1] * rows
        collage_image = Image.new('RGBA', (collage_width, collage_height), color=(255, 0, 0, 0))
        for i, img in enumerate(images):
            x = (i % columns) * thumb_size[0]
            y = (i // columns) * thumb_size[1]
            collage_image.paste(img, (x, y))
        images_bytes = BytesIO()
        collage_image.save(images_bytes, format='PNG')
        images_bytes.seek(0)
        return images_bytes