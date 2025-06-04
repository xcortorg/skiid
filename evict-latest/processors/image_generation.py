from PIL import Image, ImageEnhance, ImageDraw, ImageFilter, ImageColor, ImageFont, ImageSequence
from io import BytesIO
import math
import random
from typing import Optional
from discord.ext.commands import Context

def process_image_effect(image_bytes, effect_type, **kwargs):
    effects = {
        'deepfry': process_deepfry,
        'spin': process_spin,
        'flag': process_flag,
        'zoom': process_zoom,
        'zoomblur': process_zoomblur,
        'rainbow': process_rainbow,
        'blur': process_blur,
        'caption': process_caption,
        'meme': process_meme,
        'scramble': process_scramble,
        'reverse': process_reverse,
        'speed': process_speed
    }
    return effects[effect_type](image_bytes, **kwargs)

def process_deepfry(image_bytes, **kwargs):
    img = Image.open(BytesIO(image_bytes)).convert("RGB")
    
    enhancer = ImageEnhance.Color(img)
    img = enhancer.enhance(2.0)
    
    enhancer = ImageEnhance.Contrast(img) 
    img = enhancer.enhance(2.0)
    
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(7.0)
    
    output = BytesIO()
    img.save(output, format="PNG")
    output.seek(0)
    return output.getvalue()

def process_spin(image_bytes, **kwargs):
    img = Image.open(BytesIO(image_bytes)).convert("RGBA")
    base_size = (800, 800)
    img = img.resize(base_size, Image.Resampling.LANCZOS)
    frames = []

    for angle in range(0, 360, 10):
        rotated = img.rotate(angle, expand=False, resample=Image.Resampling.BICUBIC)
        frame = Image.new("RGBA", base_size, (0, 0, 0, 0))
        frame.paste(rotated, (0, 0), rotated)
        frames.append(frame)

    output = BytesIO()
    frames[0].save(
        output,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=50,
        loop=0,
    )
    output.seek(0)
    return output.getvalue()

def process_flag(image_bytes, **kwargs):
    img = Image.open(BytesIO(image_bytes)).convert("RGBA")
    base_size = (400, 300)
    img = img.resize(base_size, Image.Resampling.LANCZOS)
    frames = []

    for i in range(20):
        frame = img.copy()
        for x in range(frame.width):
            offset = int(math.sin(x / 30 + i / 2) * 10)
            for y in range(frame.height):
                new_y = y + offset
                if 0 <= new_y < frame.height:
                    pixel = img.getpixel((x, y))
                    frame.putpixel((x, new_y), pixel)
        frames.append(frame)

    output = BytesIO()
    frames[0].save(
        output,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=50,
        loop=0,
    )
    output.seek(0)
    return output.getvalue()

def process_zoom(image_bytes, **kwargs):
    img = Image.open(BytesIO(image_bytes)).convert("RGBA")
    base_size = (800, 800)
    img = img.resize(base_size, Image.Resampling.LANCZOS)
    frames = []

    for i in range(30):
        scale = 1 + (i * 0.1)
        size = (int(base_size[0] * scale), int(base_size[1] * scale))
        frame = img.resize(size, Image.Resampling.LANCZOS)

        new_frame = Image.new("RGBA", base_size, (0, 0, 0, 0))
        x = (base_size[0] - size[0]) // 2
        y = (base_size[1] - size[1]) // 2
        new_frame.paste(frame, (x, y))
        frames.append(new_frame)

    output = BytesIO()
    frames[0].save(
        output,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=50,
        loop=0,
    )
    output.seek(0)
    return output.getvalue()

def process_zoomblur(image_bytes, **kwargs):
    img = Image.open(BytesIO(image_bytes)).convert("RGBA")
    frames = []

    for i in range(20):
        blurred = img.copy()
        for j in range(i):
            scale = 1 + (j * 0.03)
            size = (int(img.width * scale), int(img.height * scale))
            frame = img.resize(size, Image.Resampling.LANCZOS)

            mask = Image.new("RGBA", img.size, (0, 0, 0, int(255 * (1 - j / 20))))
            x = (img.width - size[0]) // 2
            y = (img.height - size[1]) // 2
            blurred.paste(frame, (x, y), mask)

        frames.append(blurred)

    output = BytesIO()
    frames[0].save(
        output,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=50,
        loop=0,
    )
    output.seek(0)
    return output.getvalue()

def process_rainbow(image_bytes, **kwargs):
    img = Image.open(BytesIO(image_bytes)).convert("RGBA")
    frames = []

    for i in range(360):
        hue_rotation = i
        frame = img.copy()

        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        for y in range(img.height):
            color = ImageColor.getrgb(f"hsv({(hue_rotation + y/2) % 360}, 100%, 100%)")
            draw.line([(0, y), (img.width, y)], fill=color + (100,))

        frame = Image.alpha_composite(frame, overlay)
        frames.append(frame)

    output = BytesIO()
    frames[0].save(
        output,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=50,
        loop=0,
    )
    output.seek(0)
    return output.getvalue()

def process_blur(image_bytes, radius=5, **kwargs):
    img = Image.open(BytesIO(image_bytes)).convert("RGBA")
    blurred = img.filter(ImageFilter.GaussianBlur(radius=radius))

    output = BytesIO()
    blurred.save(output, format="PNG")
    output.seek(0)
    return output.getvalue()

def process_caption(image_bytes, caption, **kwargs):
    img = Image.open(BytesIO(image_bytes)).convert("RGBA")
    caption_height = int(img.width / 5)

    new_img = Image.new("RGBA", (img.width, img.height + caption_height), (255, 255, 255, 255))
    new_img.paste(img, (0, caption_height))

    draw = ImageDraw.Draw(new_img)
    font_size = int(caption_height * 0.8)
    try:
        font = ImageFont.truetype("assets/fonts/impact.ttf", font_size)
    except OSError:
        font = ImageFont.load_default()

    max_width = int(img.width * 0.9)

    def get_wrapped_text(text, font, max_width):
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            current_line.append(word)
            line = " ".join(current_line)
            bbox = draw.textbbox((0, 0), line, font=font)
            if bbox[2] - bbox[0] > max_width:
                if len(current_line) == 1:
                    lines.append(line)
                    current_line = []
                else:
                    current_line.pop()
                    lines.append(" ".join(current_line))
                    current_line = [word]

        if current_line:
            lines.append(" ".join(current_line))
        return lines

    lines = get_wrapped_text(caption, font, max_width)
    while font_size > 12:
        font = ImageFont.truetype("assets/fonts/impact.ttf", font_size)
        lines = get_wrapped_text(caption, font, max_width)

        total_height = 0
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            total_height += (bbox[3] - bbox[1]) * 1.2

        if total_height <= caption_height * 0.9:
            break

        font_size = int(font_size * 0.9)

    total_height = 0
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        total_height += (bbox[3] - bbox[1]) * 1.2

    current_y = (caption_height - total_height) / 2

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x = (img.width - text_width) / 2
        draw.text((x, current_y), line, font=font, fill="black")
        current_y += text_height * 1.2

    output = BytesIO()
    new_img.save(output, format="PNG")
    output.seek(0)
    return output.getvalue()

def process_meme(image_bytes, top_text=None, bottom_text=None, **kwargs):
    img = Image.open(BytesIO(image_bytes)).convert("RGBA")
    draw = ImageDraw.Draw(img)

    font_size = int(img.width / 12)
    try:
        font = ImageFont.truetype("assets/fonts/impact.ttf", font_size)
    except OSError:
        font = ImageFont.load_default()

    max_width = int(img.width * 0.9)

    def get_wrapped_text(text, font, max_width):
        if not text:
            return []

        words = text.upper().split()
        lines = []
        current_line = []

        for word in words:
            current_line.append(word)
            line = " ".join(current_line)
            bbox = draw.textbbox((0, 0), line, font=font)
            if bbox[2] - bbox[0] > max_width:
                if len(current_line) == 1:
                    lines.append(line)
                    current_line = []
                else:
                    current_line.pop()
                    lines.append(" ".join(current_line))
                    current_line = [word]

        if current_line:
            lines.append(" ".join(current_line))
        return lines

    def draw_text_with_outline(text, y_position, anchor="top"):
        if not text:
            return

        lines = get_wrapped_text(text, font, max_width)
        line_spacing = font_size * 1.2

        if anchor == "bottom":
            y_position = img.height - (line_spacing * len(lines)) - (font_size // 2)

        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = (img.width - text_width) / 2

            outline_width = max(1, int(font_size * 0.05))
            for adj in range(-outline_width, outline_width + 1):
                for adj2 in range(-outline_width, outline_width + 1):
                    draw.text(
                        (x + adj, y_position + adj2),
                        line,
                        font=font,
                        fill="black",
                    )

            draw.text((x, y_position), line, font=font, fill="white")
            y_position += line_spacing

    while font_size > 12:
        font = ImageFont.truetype("assets/fonts/impact.ttf", font_size)
        top_lines = get_wrapped_text(top_text, font, max_width)
        bottom_lines = get_wrapped_text(bottom_text, font, max_width)

        top_height = len(top_lines) * font_size * 1.2 if top_lines else 0
        bottom_height = len(bottom_lines) * font_size * 1.2 if bottom_lines else 0

        if top_height <= img.height * 0.25 and bottom_height <= img.height * 0.25:
            break

        font_size = int(font_size * 0.9)

    if top_text:
        draw_text_with_outline(top_text, font_size // 2, "top")

    if bottom_text:
        draw_text_with_outline(bottom_text, img.height - font_size // 2, "bottom")

    output = BytesIO()
    img.save(output, format="PNG")
    output.seek(0)
    return output.getvalue()

def process_scramble(image_bytes, **kwargs):
    img = Image.open(BytesIO(image_bytes))
    frames = [frame.copy() for frame in ImageSequence.Iterator(img)]
    random.shuffle(frames)
    
    output = BytesIO()
    frames[0].save(
        output,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=img.info.get("duration", 100),
        loop=0,
    )
    output.seek(0)
    return output.getvalue()

def process_reverse(image_bytes, **kwargs):
    img = Image.open(BytesIO(image_bytes))
    frames = [frame.copy() for frame in ImageSequence.Iterator(img)]
    frames.reverse()
    
    output = BytesIO()
    frames[0].save(
        output,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=img.info.get("duration", 100),
        loop=0,
    )
    output.seek(0)
    return output.getvalue()

def process_speed(image_bytes, speed: float = 2.0, **kwargs):
    img = Image.open(BytesIO(image_bytes))
    frames = [frame.copy() for frame in ImageSequence.Iterator(img)]
    
    output = BytesIO()
    frames[0].save(
        output,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=int(img.info.get("duration", 100) / speed),
        loop=0,
    )
    output.seek(0)
    return output.getvalue()

async def _get_media_url(
    self,
    ctx: Context,
    attachment: Optional[str],
    accept_image: bool = False,
    accept_gif: bool = False,
    accept_video: bool = False,
) -> Optional[str]:
    """Helper method to get media URL from various sources"""
    if attachment:
        return attachment

    if ctx.message.attachments:
        file = ctx.message.attachments[0]
        if accept_image and file.content_type.startswith("image/"):
            return file.url
        if accept_gif and file.filename.endswith(".gif"):
            return file.url
        if accept_video and file.content_type.startswith("video/"):
            return file.url
        return None

    if ctx.message.reference:
        referenced = await ctx.channel.fetch_message(
            ctx.message.reference.message_id
        )
        if referenced.attachments:
            file = referenced.attachments[0]
            if accept_image and file.content_type.startswith("image/"):
                return file.url
            if accept_gif and file.filename.endswith(".gif"):
                return file.url
            if accept_video and file.content_type.startswith("video/"):
                return file.url
        elif referenced.embeds:
            embed = referenced.embeds[0]
            if embed.image:
                return embed.image.url
            elif embed.thumbnail:
                return embed.thumbnail.url

    return None