import discord
from discord.ext import commands
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageSequence, ImageFilter
import os
import json
from loguru import logger
from functools import lru_cache
from typing import Dict, Tuple, Optional, List, Union
import colorsys
import asyncio

# Constants
CARD_WIDTH = 800  # Increased width for better proportions
CARD_HEIGHT = 400  # Increased height for better proportions
AVATAR_SIZE = 140  # Larger avatar
DECO_SIZE = 170  # Larger decoration
BORDER_SIZE = 80
BORDER_RADIUS = 30  # Increased radius for smoother corners
BORDER_THICKNESS = 10
BOX_WIDTH = 160  # Wider stat boxes
BOX_HEIGHT = 70  # Increased height for better text spacing
BOX_PADDING = 12
BOX_COLOR = (44, 47, 51, 180)  # Added transparency
DEFAULT_BG_COLOR = "#2f3136"

# Enhanced status colors with better visibility
STATUS_COLORS = {
    "online": (67, 181, 129, 255),  # Brighter green
    "idle": (250, 168, 26, 255),  # Warmer yellow
    "dnd": (240, 71, 71, 255),  # Brighter red
    "offline": (116, 127, 141, 255),  # Lighter grey
}

# Font paths and defaults
FONTS_DIR = "/root/greed/data/fonts"
ARIAL_BOLD_FONT_PATH = os.path.join(FONTS_DIR, "arial_bold.ttf")
DEFAULT_FONT_PATH = os.path.join(FONTS_DIR, "arial.ttf")


def create_gradient(
    width: int, height: int, color1: tuple, color2: tuple
) -> Image.Image:
    """Creates a gradient background."""
    base = Image.new("RGBA", (width, height), color1)
    top = Image.new("RGBA", (width, height), color2)
    mask = Image.new("L", (width, height))
    mask_data = []

    for y in range(height):
        mask_data.extend([int(255 * (1 - y / height))] * width)

    mask.putdata(mask_data)
    base.paste(top, (0, 0), mask)
    return base


def adjust_color_brightness(color: str, factor: float) -> tuple:
    """Adjusts the brightness of a hex color."""
    # Convert hex to RGB
    color = color.lstrip("#")
    r = int(color[:2], 16)
    g = int(color[2:4], 16)
    b = int(color[4:], 16)

    # Convert to HSV
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)

    # Adjust brightness (v)
    v = min(1.0, v * factor)

    # Convert back to RGB
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (int(r * 255), int(g * 255), int(b * 255))


@lru_cache(maxsize=10)
def get_font(font_path: str, size: int) -> ImageFont.FreeTypeFont:
    """Cache and return fonts to avoid reloading. Falls back to default font if specified font cannot be loaded."""
    try:
        return ImageFont.truetype(font_path, size)
    except (OSError, IOError) as e:
        logger.warning(f"Failed to load font {font_path}: {e}")
        try:
            # Try default font
            return ImageFont.truetype(DEFAULT_FONT_PATH, size)
        except (OSError, IOError) as e:
            logger.error(f"Failed to load default font: {e}")
            # Last resort: Use a system font that should be available
            return ImageFont.load_default()


class Card(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.message_tracking = {}
        self.user_preferences = {}
        self.decos = {}
        self.available_fonts = set()
        self.animation_cache = {}  # Cache for animated decorations
        self.bot.loop.create_task(self._initialize())

    async def _initialize(self):
        """Initialize both decorations and fonts."""
        await self.load_decos()
        self._load_available_fonts()

    def _load_available_fonts(self):
        """Load and validate available fonts."""
        self.available_fonts = set()
        try:
            if os.path.exists(FONTS_DIR):
                for file_name in os.listdir(FONTS_DIR):
                    if file_name.lower().endswith(".ttf"):
                        font_path = os.path.join(FONTS_DIR, file_name)
                        try:
                            # Verify the font can be loaded
                            ImageFont.truetype(font_path, 40)
                            self.available_fonts.add(os.path.splitext(file_name)[0])
                        except (OSError, IOError) as e:
                            logger.warning(f"Failed to load font {file_name}: {e}")

            if not self.available_fonts:
                logger.warning("No valid fonts found in fonts directory")
        except Exception as e:
            logger.error(f"Error loading fonts: {e}")

    def _get_valid_font_path(self, font_name: str) -> str:
        """Get a valid font path, falling back to default if necessary."""
        if font_name in self.available_fonts:
            return os.path.join(FONTS_DIR, f"{font_name}.ttf")
        return DEFAULT_FONT_PATH

    async def load_decos(self):
        """Loads all PNG and GIF decorations from the deco folder into a JSON file and handles APNG renaming."""
        deco_folder = "/root/greed/data/decos"
        deco_data = {}

        try:
            # Scan for decoration files
            for file_name in os.listdir(deco_folder):
                if not file_name.endswith((".png", ".apng")):
                    continue

                file_path = os.path.join(deco_folder, file_name)
                base_name = os.path.splitext(file_name)[0]

                try:
                    with Image.open(file_path) as img:
                        # Handle APNG files
                        if "apng" in img.format.lower() and file_name.endswith(".png"):
                            new_file_name = f"{base_name}.apng"
                            new_file_path = os.path.join(deco_folder, new_file_name)

                            # Only rename if necessary
                            if not os.path.exists(new_file_path):
                                os.rename(file_path, new_file_path)
                            deco_data[base_name] = new_file_path
                        else:
                            deco_data[base_name] = file_path

                except Exception as e:
                    logger.error(f"Error processing decoration {file_name}: {e}")
                    continue

            self.decos = deco_data
            logger.info(f"Loaded {len(self.decos)} decorations")

        except Exception as e:
            logger.error(f"Error loading decorations: {e}")
            self.decos = {}

    @commands.Cog.listener()
    async def on_message(self, message):
        """Tracks message count and updates rank per server."""
        try:
            if any([message.author.bot, not message.guild, not message.author]):
                return

            guild_id = str(message.guild.id)
            user_id = str(message.author.id)

            # Initialize tracking dictionaries if they don't exist
            if guild_id not in self.message_tracking:
                self.message_tracking[guild_id] = {}

            # Get or create user data with default values
            user_data = self.message_tracking[guild_id].setdefault(
                user_id, {"message_count": 0, "rank": 1}
            )

            # Update message count
            user_data["message_count"] += 1

            # Only update ranks every 10 messages to reduce processing
            if user_data["message_count"] % 10 == 0:
                await self._update_ranks(guild_id)

        except Exception as e:
            logger.error(f"Error in message tracking: {e}")

    async def _update_ranks(self, guild_id: str):
        """Updates ranks for all users in a guild."""
        try:
            guild_data = self.message_tracking[guild_id]

            # Sort users by message count
            sorted_users = sorted(
                guild_data.items(), key=lambda x: x[1]["message_count"], reverse=True
            )

            # Update ranks
            for rank, (user_id, _) in enumerate(sorted_users, 1):
                guild_data[user_id]["rank"] = rank

        except Exception as e:
            logger.error(f"Error updating ranks: {e}")

    @commands.group(name="card", invoke_without_command=True)
    async def card_group(self, ctx):
        """Main command group for user card features."""
        return await ctx.send_help(ctx.command.qualified_name)

    @commands.command(name="usercard")
    @commands.is_owner()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def user_card(self, ctx, member: discord.Member = None):
        """Generates and displays a user card with avatar, status, and banner."""
        member = member or ctx.author
        user_data = self.user_preferences.get(member.id, {})

        # Get user preferences with defaults
        background_color = user_data.get("background_color", DEFAULT_BG_COLOR)
        avatar_deco_name = user_data.get("avatar_deco", "")
        font_name = user_data.get("font", "arial.ttf")
        custom_status = user_data.get("status", member.status.name.capitalize())

        # Create base card
        card = await self._create_base_card(background_color)

        # Process avatar
        avatar_img = await self._process_avatar(member)

        # Add avatar and decoration (may return animated card)
        result = await self._add_avatar_to_card(card, avatar_img, avatar_deco_name)

        if isinstance(result, BytesIO):
            # If we got an animated result, send it directly
            await ctx.send(file=discord.File(result, filename="usercard.png"))
            return

        # If static image, continue with normal processing
        card = result

        # Add text and stats
        card = await self._add_text_and_stats(
            card, member, ctx.guild.id, font_name, custom_status
        )

        # Create final masked card
        final_card = self._create_masked_card(card)

        # Save and send
        buffer = BytesIO()
        final_card.save(buffer, format="PNG")
        buffer.seek(0)
        await ctx.send(file=discord.File(buffer, filename="usercard.png"))

    def _create_masked_card(self, card: Image.Image) -> Image.Image:
        """Creates the final masked card with proper rounded corners and no extra space."""
        # Create a mask with rounded corners
        mask = Image.new("L", (CARD_WIDTH, CARD_HEIGHT), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle(
            [0, 0, CARD_WIDTH, CARD_HEIGHT], radius=BORDER_RADIUS, fill=255
        )

        # Create a new transparent image
        final_card = Image.new("RGBA", (CARD_WIDTH, CARD_HEIGHT), (0, 0, 0, 0))

        # Paste the card using the mask
        final_card.paste(card, (0, 0), mask)

        return final_card

    async def _create_base_card(self, background_color: str) -> Image.Image:
        """Creates the base card with background and border."""
        # Create gradient background
        color1 = adjust_color_brightness(background_color, 1.2)  # Lighter
        color2 = adjust_color_brightness(background_color, 0.8)  # Darker
        card = create_gradient(CARD_WIDTH, CARD_HEIGHT, color1, color2)

        # Add subtle noise texture
        noise = Image.effect_noise((CARD_WIDTH, CARD_HEIGHT), 10).convert("RGBA")
        noise = noise.filter(ImageFilter.GaussianBlur(radius=1))
        card = Image.blend(card, noise, 0.02)

        # Add glass-like border effect
        draw = ImageDraw.Draw(card)

        # Inner shadow (slightly reduced size to prevent edge artifacts)
        shadow_color = (0, 0, 0, 50)
        draw.rounded_rectangle(
            [2, 2, CARD_WIDTH - 2, CARD_HEIGHT - 2],
            radius=BORDER_RADIUS,
            fill=None,
            outline=shadow_color,
            width=BORDER_THICKNESS,
        )

        # Main border with glass effect (slightly reduced size)
        border_color = (*adjust_color_brightness(background_color, 1.3), 180)
        draw.rounded_rectangle(
            [1, 1, CARD_WIDTH - 1, CARD_HEIGHT - 1],
            radius=BORDER_RADIUS,
            fill=None,
            outline=border_color,
            width=BORDER_THICKNESS // 2,
        )

        return card

    async def _process_avatar(self, member: discord.Member) -> Image.Image:
        """Processes and returns the user's avatar."""
        avatar_url = member.avatar.url if member.avatar else member.default_avatar.url
        avatar_response = await self.fetch_image(avatar_url)
        avatar_img = Image.open(BytesIO(avatar_response)).convert("RGBA")

        # Resize with high-quality resampling
        avatar_img = avatar_img.resize((AVATAR_SIZE, AVATAR_SIZE), Image.LANCZOS)

        # Create circular mask with anti-aliasing
        mask = Image.new("L", (AVATAR_SIZE, AVATAR_SIZE), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, AVATAR_SIZE, AVATAR_SIZE), fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(radius=0.5))

        # Apply mask
        avatar_img.putalpha(mask)

        # Add subtle inner shadow
        shadow = Image.new("RGBA", (AVATAR_SIZE, AVATAR_SIZE), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.ellipse(
            (2, 2, AVATAR_SIZE - 2, AVATAR_SIZE - 2), fill=(0, 0, 0, 50)
        )
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=2))

        # Composite shadow and avatar
        avatar_img = Image.alpha_composite(avatar_img, shadow)

        return avatar_img

    def _process_animation(self, img: Image.Image) -> List[Image.Image]:
        """Process an animated image and return its frames."""
        frames = []
        try:
            for frame in ImageSequence.Iterator(img):
                # Convert to RGBA to ensure transparency support
                frame_copy = frame.convert("RGBA")
                frames.append(frame_copy)
            return frames
        except Exception as e:
            logger.error(f"Error processing animation frames: {e}")
            return [img.convert("RGBA")]  # Return single frame if animation fails

    def _resize_animation(
        self, frames: List[Image.Image], size: tuple
    ) -> List[Image.Image]:
        """Resize all frames of an animation."""
        return [frame.resize(size, Image.LANCZOS) for frame in frames]

    def _create_circular_mask(self, size: tuple) -> Image.Image:
        """Create a circular mask for frames."""
        mask = Image.new("L", size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size[0], size[1]), fill=255)
        return mask.filter(ImageFilter.GaussianBlur(radius=0.5))

    def _apply_mask_to_frames(
        self, frames: List[Image.Image], mask: Image.Image
    ) -> List[Image.Image]:
        """Apply mask to all frames."""
        return [frame.copy().putalpha(mask) for frame in frames]

    async def _create_animated_card(
        self,
        card_base: Image.Image,
        avatar_img: Image.Image,
        deco_frames: List[Image.Image],
    ) -> BytesIO:
        """Create an animated card with the decoration frames."""
        buffer = BytesIO()
        output_frames = []

        # Calculate positions
        avatar_x = 60
        avatar_y = (CARD_HEIGHT - AVATAR_SIZE) // 2
        deco_x = avatar_x - 15
        deco_y = avatar_y - 15

        # Create frames for each decoration frame
        for deco_frame in deco_frames:
            # Create a new copy of the base card for this frame
            frame = card_base.copy()

            # Add avatar (use the already processed avatar_img)
            frame.paste(avatar_img, (avatar_x, avatar_y), avatar_img)

            # Add decoration frame
            frame.paste(deco_frame, (deco_x, deco_y), deco_frame)

            # Apply final masking
            frame = self._create_masked_card(frame)
            output_frames.append(frame)

        # Save as animated PNG
        output_frames[0].save(
            buffer,
            format="PNG",
            save_all=True,
            append_images=output_frames[1:],
            duration=100,  # Adjust duration as needed
            loop=0,
        )
        buffer.seek(0)
        return buffer

    async def _add_avatar_to_card(
        self, card: Image.Image, avatar_img: Image.Image, deco_name: str
    ) -> Union[Image.Image, BytesIO]:
        """Adds the avatar and decoration to the card, handling both static and animated decorations."""
        try:
            # Add glow effect
            glow = Image.new("RGBA", (AVATAR_SIZE + 20, AVATAR_SIZE + 20), (0, 0, 0, 0))
            glow_draw = ImageDraw.Draw(glow)
            glow_draw.ellipse(
                (0, 0, AVATAR_SIZE + 20, AVATAR_SIZE + 20), fill=(255, 255, 255, 30)
            )
            glow = glow.filter(ImageFilter.GaussianBlur(radius=10))

            # Calculate positions
            avatar_x = 60
            avatar_y = (CARD_HEIGHT - AVATAR_SIZE) // 2

            # Add glow to base card
            card.paste(glow, (avatar_x - 10, avatar_y - 10), glow)

            # Add avatar to card first
            card.paste(avatar_img, (avatar_x, avatar_y), avatar_img)

            # Handle decoration if specified
            if deco_name:
                deco_path = self._get_deco_path(deco_name)
                if not deco_path:
                    logger.error(f"Decoration path not found for {deco_name}")
                    return card

                try:
                    # Check cache first
                    if deco_path in self.animation_cache:
                        logger.debug(f"Using cached frames for {deco_name}")
                        deco_frames = self.animation_cache[deco_path]
                    else:
                        logger.debug(f"Loading decoration from {deco_path}")
                        with Image.open(deco_path) as deco_img:
                            # Check if image is animated
                            is_animated = (
                                hasattr(deco_img, "n_frames") and deco_img.n_frames > 1
                            )

                            if is_animated:
                                # Process animation frames
                                deco_frames = self._process_animation(deco_img)
                                deco_frames = self._resize_animation(
                                    deco_frames, (DECO_SIZE, DECO_SIZE)
                                )
                                # Cache the processed frames
                                self.animation_cache[deco_path] = deco_frames
                                logger.debug(
                                    f"Cached {len(deco_frames)} frames for {deco_name}"
                                )
                            else:
                                # Handle static image
                                deco_img = deco_img.convert("RGBA").resize(
                                    (DECO_SIZE, DECO_SIZE), Image.LANCZOS
                                )
                                deco_frames = [deco_img]

                    if len(deco_frames) > 1:
                        # Create animated card
                        logger.debug(
                            f"Creating animated card with {len(deco_frames)} frames"
                        )
                        return await self._create_animated_card(
                            card, avatar_img, deco_frames
                        )
                    else:
                        # Handle static decoration
                        deco_img = deco_frames[0]
                        x = avatar_x - 15
                        y = avatar_y - 15

                        # Create a copy of the card before pasting decoration
                        card_with_deco = card.copy()
                        card_with_deco.paste(deco_img, (x, y), deco_img)
                        logger.debug(f"Added static decoration {deco_name}")
                        return card_with_deco

                except Exception as e:
                    logger.error(
                        f"Error applying decoration {deco_name}: {e}", exc_info=True
                    )
                    return card

            return card

        except Exception as e:
            logger.error(f"Error in _add_avatar_to_card: {e}", exc_info=True)
            return card

    def _get_deco_path(self, deco_name: str) -> Optional[str]:
        """Returns the path to the decoration image."""
        return self.decos.get(deco_name)

    async def _add_text_and_stats(
        self,
        card: Image.Image,
        member: discord.Member,
        guild_id: int,
        font_name: str,
        status: str,
    ) -> Image.Image:
        """Adds username, status, and stats to the card."""
        draw = ImageDraw.Draw(card)

        # Load fonts with proper fallback
        main_font = get_font(self._get_valid_font_path(font_name), 48)  # Larger font
        stats_font = get_font(ARIAL_BOLD_FONT_PATH, 20)  # Larger stats font

        # Add text shadow effect
        def draw_text_with_shadow(x, y, text, font, color):
            # Draw shadow
            shadow_color = (0, 0, 0, 100)
            draw.text((x + 2, y + 2), text, font=font, fill=shadow_color)
            # Draw main text
            draw.text((x, y), text, font=font, fill=color)

        # Draw username with shadow
        draw_text_with_shadow(240, 140, member.name, main_font, (255, 255, 255, 255))

        # Draw status with glow effect
        status_words = " ".join(status.split()[:4])
        status_color = STATUS_COLORS.get(status_words.lower(), (255, 255, 255, 255))

        # Status indicator circle
        circle_x, circle_y = 240, 200
        circle_radius = 8
        draw.ellipse(
            [
                circle_x,
                circle_y,
                circle_x + circle_radius * 2,
                circle_y + circle_radius * 2,
            ],
            fill=status_color,
        )

        # Draw status text
        draw_text_with_shadow(265, 195, status_words, stats_font, status_color)

        # Get and draw stats with modern box design
        message_count, server_rank = self._get_user_stats(str(guild_id), str(member.id))

        # Function to draw modern stat box
        def draw_stat_box(x, y, label, value):
            # Box background with gradient
            box_gradient = create_gradient(
                BOX_WIDTH,
                BOX_HEIGHT,
                (*BOX_COLOR[:3], 150),  # More transparent at top
                (*BOX_COLOR[:3], 200),  # Less transparent at bottom
            )
            card.paste(box_gradient, (x, y), box_gradient)

            # Draw stat value
            value_font = get_font(ARIAL_BOLD_FONT_PATH, 24)
            label_font = get_font(ARIAL_BOLD_FONT_PATH, 16)

            # Center align text
            value_w = value_font.getlength(str(value))
            label_w = label_font.getlength(label)

            value_x = x + (BOX_WIDTH - value_w) // 2
            label_x = x + (BOX_WIDTH - label_w) // 2

            # Adjusted vertical positioning - value at top, label at bottom with more space
            draw_text_with_shadow(
                value_x, y + 12, str(value), value_font, (255, 255, 255, 255)
            )
            draw_text_with_shadow(
                label_x, y + BOX_HEIGHT - 30, label, label_font, (200, 200, 200, 255)
            )

        # Draw stat boxes
        draw_stat_box(240, 260, "MESSAGES", message_count)
        draw_stat_box(240 + BOX_WIDTH + 20, 260, "RANK", f"#{server_rank}")

        return card

    def _get_user_stats(self, guild_id: str, user_id: str) -> Tuple[int, int]:
        """Returns message count and server rank for a user."""
        user_data = self.message_tracking.get(guild_id, {}).get(user_id, {})
        return (user_data.get("message_count", 0), user_data.get("rank", 1))

    @card_group.command(name="font")
    async def set_font(self, ctx, font_name: str = "arial"):
        """Set a custom font for the user's name in the user card."""
        if font_name not in self.available_fonts:
            available_fonts = "`, `".join(sorted(self.available_fonts)) or "None"
            return await ctx.fail(
                f"The font `{font_name}` is not available. Available fonts: `{available_fonts}`"
            )

        if ctx.author.id not in self.user_preferences:
            self.user_preferences[ctx.author.id] = {}

        self.user_preferences[ctx.author.id]["font"] = font_name
        await ctx.success(f"Your font has been updated to `{font_name}`.")

    @card_group.command(name="decos")
    async def list_decos(self, ctx):
        """Lists all available avatar decorations in a paginated format with previews."""
        if not self.decos:
            return await ctx.send("No decorations are available.")

        # Get booster status
        is_booster = (
            await self.bot.db.fetchrow(
                """SELECT * FROM boosters WHERE user_id = $1""", ctx.author.id
            )
            is not None
        )

        # Sort decorations by name
        deco_names = sorted(self.decos.keys())

        # Create embeds with 6 decorations per page
        embeds = []
        for i in range(0, len(deco_names), 6):
            page_decos = deco_names[i : i + 6]

            embed = discord.Embed(title="Available Decorations", color=ctx.author.color)

            # Add booster status message
            if not is_booster:
                embed.description = "⭐ **Boost [/greedbot](https://discord.gg/greedbot) to use decorations!**\n\n"
            else:
                embed.description = "✨ **You can use these decorations!**\n\n"

            # Add decorations to the embed
            for deco_name in page_decos:
                # Check if user has this decoration equipped
                is_equipped = (
                    self.user_preferences.get(ctx.author.id, {}).get("avatar_deco", "")
                    == deco_name
                )

                # Format the decoration name
                display_name = f"{'🔸' if is_equipped else '•'} `{deco_name}`"

                # Add file type indicator
                deco_path = self.decos.get(deco_name)
                is_animated = deco_path and deco_path.endswith(".apng")
                type_indicator = "[Animated]" if is_animated else "[Static]"

                embed.add_field(
                    name=display_name,
                    value=f"{type_indicator}\n{'(Currently equipped)' if is_equipped else ''}",
                    inline=True,
                )

            # Add page number and total pages
            total_pages = (len(deco_names) + 5) // 6
            embed.set_footer(
                text=f"Page {i//6 + 1}/{total_pages} • Use !card deco <name> to equip"
            )

            embeds.append(embed)

        # Send paginated embeds
        await ctx.paginate(embeds)

    @card_group.command(name="color")
    async def set_bg_color(self, ctx, color: str):
        """Allows users to customize the background color of their user card."""
        # Validate hex color
        if not color.startswith("#") or len(color) != 7:
            return await ctx.fail(
                "Please provide a valid hex color code (e.g., #2f3136)."
            )

        # Update the user's background color in the in-memory dictionary
        if ctx.author.id not in self.user_preferences:
            self.user_preferences[ctx.author.id] = {}

        self.user_preferences[ctx.author.id]["background_color"] = color
        await ctx.success(f"Your background color has been updated to `{color}`.")

    @card_group.command(name="deco")
    async def set_avatar_deco(self, ctx, deco_name: str = None):
        """Allows users to set or remove an avatar decoration for their user card."""
        # Check booster status
        is_booster = await self.bot.db.fetchrow(
            """SELECT * FROM boosters WHERE user_id = $1""", ctx.author.id
        )
        if not is_booster:
            return await ctx.fail(
                "You need to boost [/greedbot](https://discord.gg/greedbot) to use decorations!"
            )

        # If no decoration name provided, show current decoration
        if deco_name is None:
            current_deco = self.user_preferences.get(ctx.author.id, {}).get(
                "avatar_deco", None
            )
            if current_deco:
                return await ctx.info(
                    f"Your current decoration is `{current_deco}`.\nUse `!card decos` to see all available decorations."
                )
            else:
                return await ctx.info(
                    "You don't have any decoration equipped.\nUse `!card decos` to see all available decorations."
                )

        # Handle decoration removal
        if deco_name.lower() in ["none", "remove", "off"]:
            if ctx.author.id in self.user_preferences:
                self.user_preferences[ctx.author.id].pop("avatar_deco", None)
            return await ctx.success("Your avatar decoration has been removed.")

        # Check if the decoration exists
        if deco_name not in self.decos:
            # Create a more compact error message
            similar_decos = [
                d for d in self.decos.keys() if deco_name.lower() in d.lower()
            ]
            error_msg = f"The decoration `{deco_name}` does not exist."

            if similar_decos:
                # If there are similar decorations, suggest them
                suggestions = ", ".join(f"`{d}`" for d in similar_decos[:5])
                if len(similar_decos) > 5:
                    error_msg += f"\n\nSimilar decorations: {suggestions} and {len(similar_decos) - 5} more..."
                else:
                    error_msg += f"\n\nSimilar decorations: {suggestions}"

            error_msg += "\n\nUse `!card decos` to see all available decorations."
            return await ctx.fail(error_msg)

        # Update the user's avatar decoration
        if ctx.author.id not in self.user_preferences:
            self.user_preferences[ctx.author.id] = {}

        self.user_preferences[ctx.author.id]["avatar_deco"] = deco_name

        # Get decoration type
        deco_path = self._get_deco_path(deco_name)
        deco_type = (
            "animated" if deco_path and deco_path.endswith(".apng") else "static"
        )

        await ctx.success(
            f"Your avatar decoration has been updated to `{deco_name}` ({deco_type}).\n"
            "Use `!usercard` to see how it looks!"
        )

    async def fetch_image(self, url: str):
        """Helper method to fetch an image from a URL."""
        async with self.bot.session.get(url) as response:
            return await response.read()


# Cog setup
async def setup(bot):
    await bot.add_cog(Card(bot))
