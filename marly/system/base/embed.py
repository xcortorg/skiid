import random
import urllib

import dateparser
from discord import ButtonStyle, Color, Embed, Member, Message, TextChannel, Webhook
from discord.ext.commands import CommandError, Converter
from discord.ui import Button, View  # type: ignore
from discord.utils import escape_markdown, utcnow

from system import tagscript
from system.tools.converters.color import colors
from system.base.context import Context
from datetime import datetime
from pytz import timezone
from system.tools.regex import IMAGE_URL, URL

from system.tools.utils import comma, ordinal, hidden


class LinkButton(Button):
    def __init__(
        self,
        label: str,
        url: str,
        emoji: str,
        style: ButtonStyle = ButtonStyle.link,
    ):
        super().__init__(style=style, label=label, url=url, emoji=emoji)


class LinkView(View):
    def __init__(self, links: list[LinkButton]):
        super().__init__(timeout=None)
        for button in links:
            self.add_item(button)


def get_color(value: str):
    if value.lower() in {"random", "rand", "r"}:
        return Color.random()
    if value.lower() in {"invisible", "invis"}:
        return Color.from_str("#2B2D31")
    if value.lower() in {"blurple", "blurp"}:
        return Color.blurple()
    if value.lower() in {"black", "negro"}:
        return Color.from_str("#000001")

    value = colors.get(value.lower()) or value
    try:
        color = Color(int(value.replace("#", ""), 16))
    except ValueError:
        return None

    return color if color.value <= 16777215 else None


class EmbedScript:
    def __init__(self, script: str):
        self.script: str = script
        self._script: str = script
        self._type: str = "text"
        self.parser: tagscript.Parser = tagscript.Parser()
        self.embed_parser: tagscript.Parser = tagscript.Parser()
        self.objects: dict = dict(content=None, embed=Embed(), embeds=[], button=[])

        # Initialize 'tags' as lists instead of dictionaries
        self.parser.tags = []  # Changed from {} to []
        self.embed_parser.tags = []  # Changed from {} to []

        # Register parser methods
        self.register_parser_methods()
        self.register_embed_parser_methods()

    def register_parser_methods(self):
        """Registers all the tag methods for the main parser."""
        parser = self.parser

        @parser.method(
            name="lower",
            usage="(value)",
            aliases=["lowercase"],
        )
        async def lower(context, value: str):
            """Convert the value to lowercase"""
            return value.lower()

        @parser.method(
            name="upper",
            usage="(value)",
            aliases=["uppercase"],
        )
        async def upper(context, value: str):
            """Convert the value to uppercase"""
            return value.upper()

        @parser.method(
            name="hidden",
            usage="(value)",
            aliases=["hide"],
        )
        async def _hidden(context, value: str):
            """Hide the value"""
            return hidden(value)

        @parser.method(
            name="quote",
            usage="(value)",
            aliases=["http"],
        )
        async def quote(context, value: str):
            """Format the value for a URL"""
            return urllib.parse.quote(value, safe="")

        @parser.method(
            name="len",
            usage="(value)",
            aliases=["length", "size", "count"],
        )
        async def length(context, value: str):
            """Get the length of the value"""
            if ", " in value:
                return len(value.split(", "))
            if "," in value:
                value = value.replace(",", "")
                if value.isnumeric():
                    return int(value)
            return len(value)

        @parser.method(
            name="strip",
            usage="(text) (removal)",
            aliases=["remove"],
        )
        async def _strip(context, text: str, removal: str):
            """Remove a value from text"""
            return text.replace(removal, "")

        @parser.method(
            name="random",
            usage="(items)",
            aliases=["choose", "choice"],
        )
        async def _random(context, *items):
            """Chooses a random item"""
            if not items:
                raise CommandError("No items provided for random selection.")
            return random.choice(items)

        @parser.method(
            name="if",
            usage="(condition) (value if true) (value if false)",
            aliases=["%"],
        )
        async def if_statement(context, condition, output, err=""):
            """If the condition is true, return the output, else return the error"""
            condition, output, err = str(condition), str(output), str(err)
            if output.startswith("{") and not output.endswith("}"):
                output += "}"
            if err.startswith("{") and not err.endswith("}"):
                err += "}"

            if "==" in condition:
                condition = condition.split("==")
                if condition[0].lower().strip() == condition[1].lower().strip():
                    return output
                return err
            if "!=" in condition:
                condition = condition.split("!=")
                if condition[0].lower().strip() != condition[1].lower().strip():
                    return output
                return err
            if ">=" in condition:
                condition = condition.split(">=")
                if "," in condition[0]:
                    condition[0] = condition[0].replace(",", "")
                if "," in condition[1]:
                    condition[1] = condition[1].replace(",", "")
                if int(condition[0].strip()) >= int(condition[1].strip()):
                    return output
                return err
            if "<=" in condition:
                condition = condition.split("<=")
                if "," in condition[0]:
                    condition[0] = condition[0].replace(",", "")
                if "," in condition[1]:
                    condition[1] = condition[1].replace(",", "")
                if int(condition[0].strip()) <= int(condition[1].strip()):
                    return output
                return err
            if ">" in condition:
                condition = condition.split(">")
                if "," in condition[0]:
                    condition[0] = condition[0].replace(",", "")
                if "," in condition[1]:
                    condition[1] = condition[1].replace(",", "")
                return (
                    output
                    if int(condition[0].strip()) > int(condition[1].strip())
                    else err
                )
            if "<" in condition:
                condition = condition.split("<")
                if "," in condition[0]:
                    condition[0] = condition[0].replace(",", "")
                if "," in condition[1]:
                    condition[1] = condition[1].replace(",", "")
                return (
                    output
                    if int(condition[0].strip()) < int(condition[1].strip())
                    else err
                )
            if condition.lower().strip() not in (
                "null",
                "no",
                "false",
                "none",
                "",
            ):
                return output
            return err

        @parser.method(
            name="message",
            usage="(value)",
            aliases=["content", "msg"],
        )
        async def message(context, value: str):
            """Set the message content"""
            self.objects["content"] = value
            return ""  # Prevent replacement in the script

        @parser.method(
            name="button",
            usage="(url) (label: optional) (emoji: optional)",
        )
        async def button(context, url: str, label: str = None, emoji: str = None):
            """Add a link to the message"""
            # Validate URL
            if not URL.match(url):
                raise CommandError("Invalid URL provided for button")

            # URL encode if needed
            if not url.startswith(("http://", "https://")):
                url = f"https://{url}"

            # Clean label/emoji inputs
            _label = None
            _emoji = None

            if label and label.lower() not in (
                "null",
                "none",
                "no",
                "false",
                "off",
            ):
                _label = label

            if emoji and emoji.lower() not in (
                "null",
                "none",
                "no",
                "false",
                "off",
            ):
                _emoji = emoji

            # Discord requires either a label or emoji
            if not _label and not _emoji:
                raise CommandError("Button must have either a label or emoji")

            button_data = {
                "url": url,
                "label": _label or "\u200b",
                "emoji": _emoji,
            }

            self.objects["button"].append(button_data)
            return ""  # Prevent replacement in the script

    def register_embed_parser_methods(self):
        """Registers all the tag methods for the embed parser."""
        embed_parser = self.embed_parser

        @embed_parser.method(
            name="color",
            usage="(value)",
            aliases=["colour", "c"],
        )
        async def embed_color(context, value: str):
            """Set the color of the embed"""
            color = get_color(value)
            if color:
                self.objects["embed"].color = color
            else:
                raise CommandError(f"Invalid color value: {value}")
            return ""  # Prevent replacement in the script

        @embed_parser.method(
            name="author",
            usage="(name) <icon url> <url>",
            aliases=["a"],
        )
        async def embed_author(
            context, name: str, icon_url: str = None, url: str = None
        ):
            """Set the author of the embed"""
            if icon_url and icon_url.lower() in {
                "off",
                "no",
                "none",
                "null",
                "false",
                "disable",
            }:
                icon_url = None
            elif (
                icon_url
                and (match := URL.match(str(icon_url)))
                and not IMAGE_URL.match(str(icon_url))
            ):
                icon_url = None
                url = match.group()

            self.objects["embed"].set_author(name=name, icon_url=icon_url, url=url)
            return ""  # Prevent replacement in the script

        @embed_parser.method(
            name="url",
            usage="(value)",
            aliases=["uri", "u"],
        )
        async def embed_url(context, value: str):
            """Set the url of the embed"""
            self.objects["embed"].url = value
            return ""  # Prevent replacement in the script

        @embed_parser.method(name="title", usage="(value)", aliases=["t"])
        async def embed_title(context, value: str):
            """Set the title of the embed"""
            self.objects["embed"].title = value
            return ""  # Prevent replacement in the script

        @embed_parser.method(name="description", usage="(value)", aliases=["desc", "d"])
        async def embed_description(context, value: str):
            """Set the description of the embed"""
            # Trim any extra whitespace before setting the description
            value = value.strip()

            # Check character limit
            if len(value) > 1000:
                raise CommandError("Description cannot exceed 1000 characters")

            self.objects["embed"].description = value
            return ""  # Prevent replacement in the script

        @embed_parser.method(
            name="field", usage="(name) (value) <inline>", aliases=["f"]
        )
        async def embed_field(context, name: str, value: str, inline: bool = True):
            """Add a field to the embed"""
            self.objects["embed"].add_field(name=name, value=value, inline=inline)
            return ""  # Prevent replacement in the script

        @embed_parser.method(
            name="thumbnail",
            usage="(url)",
            aliases=["thumb", "t"],
        )
        async def embed_thumbnail(context, url: str = None):
            """Set the thumbnail of the embed"""
            self.objects["embed"].set_thumbnail(url=url)
            return ""  # Prevent replacement in the script

        @embed_parser.method(
            name="image",
            usage="(url)",
            aliases=["img", "i"],
        )
        async def embed_image(context, url: str = None):
            """Set the image of the embed"""
            self.objects["embed"].set_image(url=url)
            return ""  # Prevent replacement in the script

        @embed_parser.method(
            name="footer",
            usage="(text) <icon url>",
            aliases=["f"],
        )
        async def embed_footer(context, text: str, icon_url: str = None):
            """Set the footer of the embed"""
            self.objects["embed"].set_footer(text=text, icon_url=icon_url)
            return ""  # Prevent replacement in the script

        @embed_parser.method(
            name="timestamp",
            usage="(value)",
            aliases=["t"],
        )
        async def embed_timestamp(context, value: str = "now"):
            """Set the timestamp of the embed"""
            if value.lower() in {"now", "current", "today"}:
                self.objects["embed"].timestamp = utcnow()
            else:
                parsed_time = dateparser.parse(value)
                if parsed_time:
                    self.objects["embed"].timestamp = parsed_time
                else:
                    raise CommandError(f"Invalid timestamp value: {value}")
            return ""  # Prevent replacement in the script

    async def resolve_variables(self, script: str = None, **kwargs):
        """Format the variables inside the script"""
        # Use provided script or instance script
        script_to_resolve = script if script is not None else self.script

        # Get current time in PST and UTC
        pst_now = datetime.now(timezone("US/Pacific"))
        utc_now = datetime.now(timezone("UTC"))

        # Add date/time variables
        script_to_resolve = (
            script_to_resolve
            # PST dates
            .replace("{date.now}", pst_now.strftime("%Y-%m-%d"))
            .replace("{date.now_proper}", pst_now.strftime("%B %d, %Y"))
            .replace("{date.now_short}", pst_now.strftime("%b %d, %Y"))
            .replace("{date.now_shorter}", pst_now.strftime("%m/%d/%y"))
            .replace("{time.now}", pst_now.strftime("%I:%M %p"))
            .replace("{time.now_military}", pst_now.strftime("%H:%M"))
            # UTC dates
            .replace("{date.utc_timestamp}", str(int(utc_now.timestamp())))
            .replace("{date.utc_now}", utc_now.strftime("%Y-%m-%d"))
            .replace("{date.utc_now_proper}", utc_now.strftime("%B %d, %Y"))
            .replace("{date.utc_now_short}", utc_now.strftime("%b %d, %Y"))
            .replace("{date.utc_now_shorter}", utc_now.strftime("%m/%d/%y"))
            .replace("{time.utc_now}", utc_now.strftime("%I:%M %p"))
            .replace("{time.utc_now_military}", utc_now.strftime("%H:%M"))
        )

        if guild := kwargs.get("guild"):
            script_to_resolve = (
                script_to_resolve.replace("{guild}", str(guild))
                .replace("{guild.id}", str(guild.id))
                .replace("{guild.name}", str(guild.name))
                .replace(
                    "{guild.icon}",
                    str(guild.icon or "https://cdn.discordapp.com/embed/avatars/1.png"),
                )
                .replace("{guild.banner}", str(guild.banner or "No banner"))
                .replace("{guild.splash}", str(guild.splash or "No splash"))
                .replace("{guild.shard}", str(guild.shard_id))
                .replace(
                    "{guild.discovery_splash}",
                    str(guild.discovery_splash or "No discovery splash"),
                )
                .replace("{guild.owner}", str(guild.owner))
                .replace("{guild.owner_id}", str(guild.owner_id))
                .replace("{guild.count}", str(comma(len(guild.members))))
                .replace("{guild.members}", str(comma(len(guild.members))))
                .replace("{len(guild.members)}", str(comma(len(guild.members))))
                .replace("{guild.channels}", str(comma(len(guild.channels))))
                .replace("{guild.boost_count}", str(guild.premium_subscription_count))
                .replace("{guild.boost_tier}", str(guild.premium_tier or "No Level"))
                .replace("{guild.preferred_locale}", str(guild.preferred_locale))
                .replace("{guild.key_features}", ", ".join(guild.features) or "N/A")
                .replace("{guild.max_presences}", str(guild.max_presences))
                .replace("{guild.max_members}", str(guild.max_members))
                .replace(
                    "{guild.max_video_channel_users}",
                    str(guild.max_video_channel_users),
                )
                .replace("{guild.afk_timeout}", str(guild.afk_timeout))
                .replace("{guild.afk_channel}", str(guild.afk_channel or "N/A"))
                .replace("{guild.system_channel}", str(guild.system_channel or "N/A"))
                .replace(
                    "{guild.system_channel_flags}",
                    str(guild.system_channel_flags or "N/A"),
                )
                .replace(
                    "{guild.created_at_timestamp}",
                    str(int(guild.created_at.timestamp())),
                )
                .replace(
                    "{guild.discovery}",
                    str(
                        guild.discovery_splash.url if guild.discovery_splash else "N/A"
                    ),
                )
                .replace("{guild.channels_count}", str(comma(len(guild.channels))))
                .replace(
                    "{guild.text_channels_count}", str(comma(len(guild.text_channels)))
                )
                .replace(
                    "{guild.voice_channels_count}",
                    str(comma(len(guild.voice_channels))),
                )
                .replace(
                    "{guild.category_channels_count}", str(comma(len(guild.categories)))
                )
                .replace(
                    "{guild.channel_count}",
                    str(comma(len(guild.channels))),
                )
                .replace(
                    "{guild.category_channels}",
                    str(comma(len(guild.categories))),
                )
                .replace(
                    "{guild.category_channel_count}",
                    str(comma(len(guild.categories))),
                )
                .replace(
                    "{guild.text_channels}",
                    str(comma(len(guild.text_channels))),
                )
                .replace(
                    "{guild.text_channel_count}",
                    str(comma(len(guild.text_channels))),
                )
                .replace(
                    "{guild.voice_channels}",
                    str(comma(len(guild.voice_channels))),
                )
                .replace(
                    "{guild.voice_channel_count}",
                    str(comma(len(guild.voice_channels))),
                )
                .replace("{guild.roles}", str(comma(len(guild.roles))))
                .replace("{guild.role_count}", str(comma(len(guild.roles))))
                .replace("{guild.emojis}", str(comma(len(guild.emojis))))
                .replace("{guild.emoji_count}", str(comma(len(guild.emojis))))
                .replace(
                    "{guild.created_at}",
                    str(guild.created_at.strftime("%m/%d/%Y, %I:%M %p")),
                )
                .replace(
                    "{unix(guild.created_at)}",
                    str(guild.created_at.timestamp()),
                )
            )
        if channel := kwargs.get("channel"):
            if isinstance(channel, TextChannel):
                script_to_resolve = (
                    script_to_resolve.replace("{channel}", str(channel))
                    .replace("{channel.id}", str(channel.id))
                    .replace("{channel.mention}", str(channel.mention))
                    .replace("{channel.name}", str(channel.name))
                    .replace("{channel.topic}", str(channel.topic))
                    .replace("{channel.created_at}", str(channel.created_at))
                    .replace("{channel.type}", str(channel.type))
                    .replace(
                        "{channel.category_id}",
                        str(getattr(channel, "category_id", "N/A")),
                    )
                    .replace(
                        "{channel.category_name}",
                        str(getattr(channel, "category", "N/A")),
                    )
                    .replace("{channel.position}", str(channel.position))
                    .replace(
                        "{channel.slowmode_delay}",
                        str(getattr(channel, "slowmode_delay", 0)),
                    )
                )
                # Continue with additional replacements as needed...

        if user := kwargs.get("user"):
            script_to_resolve = (
                script_to_resolve.replace("{user}", str(user))
                .replace("{user.id}", str(user.id))
                .replace("{user.mention}", str(user.mention))
                .replace("{user.name}", str(user.name))
                .replace("{user.bot}", "Yes" if user.bot else "No")
                .replace("{user.color}", str(user.color))
                .replace("{user.avatar}", str(user.display_avatar))
                .replace("{user.nickname}", str(user.display_name))
                .replace("{user.nick}", str(user.display_name))
                .replace(
                    "{user.created_at}",
                    str(user.created_at.strftime("%m/%d/%Y, %I:%M %p")),
                )
                .replace(
                    "{unix(user.created_at)}",
                    str(int(user.created_at.timestamp())),
                )
                .replace(
                    "{user.boost_since_timestamp}",
                    (
                        str(int(user.premium_since.timestamp()))
                        if isinstance(user, Member) and user.premium_since
                        else "Never"
                    ),
                )
                .replace(
                    "{user.join_position}",
                    (
                        str(
                            sorted(guild.members, key=lambda m: m.joined_at).index(user)
                            + 1
                        )
                        if isinstance(user, Member) and guild
                        else "N/A"
                    ),
                )
                .replace(
                    "{user.guild_avatar}", str(user.guild_avatar or user.display_avatar)
                )
                .replace("{user.top_role}", str(getattr(user, "top_role", "N/A")))
                .replace(
                    "{user.role_list}",
                    ", ".join(
                        [r.name for r in user.roles[1:]]
                        if isinstance(user, Member)
                        else "N/A"
                    ),
                )
                .replace(
                    "{user.role_text_list}",
                    ", ".join(
                        [r.name for r in user.roles[1:]]
                        if isinstance(user, Member)
                        else "N/A"
                    ),
                )
                .replace(
                    "{user.join_position_suffix}",
                    str(
                        ordinal(
                            sorted(guild.members, key=lambda m: m.joined_at).index(user)
                            + 1
                        )
                    ),
                )
                .replace(
                    "{user.created_at}",
                    str(user.created_at.strftime("%m/%d/%Y, %I:%M %p")),
                )
                .replace(
                    "{unix(user.created_at)}",
                    str(int(user.created_at.timestamp())),
                )
            )
            if isinstance(user, Member):
                script_to_resolve = (
                    script_to_resolve.replace(
                        "{user.joined_at}",
                        str(user.joined_at.strftime("%m/%d/%Y, %I:%M %p")),
                    )
                    .replace("{user.boost}", "Yes" if user.premium_since else "No")
                    .replace(
                        "{user.boosted_at}",
                        (
                            str(user.premium_since.strftime("%m/%d/%Y, %I:%M %p"))
                            if user.premium_since
                            else "Never"
                        ),
                    )
                    .replace(
                        "{unix(user.boosted_at)}",
                        (
                            str(int(user.premium_since.timestamp()))
                            if user.premium_since
                            else "Never"
                        ),
                    )
                    .replace(
                        "{user.boost_since}",
                        (
                            str(user.premium_since.strftime("%m/%d/%Y, %I:%M %p"))
                            if user.premium_since
                            else "Never"
                        ),
                    )
                    .replace(
                        "{unix(user.boost_since)}",
                        (
                            str(int(user.premium_since.timestamp()))
                            if user.premium_since
                            else "Never"
                        ),
                    )
                )

        if moderator := kwargs.get("moderator"):
            script_to_resolve = (
                script_to_resolve.replace("{moderator}", str(moderator))
                .replace("{moderator.id}", str(moderator.id))
                .replace("{moderator.mention}", str(moderator.mention))
                .replace("{moderator.name}", str(moderator.name))
                .replace("{moderator.bot}", "Yes" if moderator.bot else "No")
                .replace("{moderator.color}", str(moderator.color))
                .replace("{moderator.avatar}", str(moderator.display_avatar))
                .replace("{moderator.nickname}", str(moderator.display_name))
                .replace("{moderator.nick}", str(moderator.display_name))
                .replace(
                    "{moderator.created_at}",
                    str(moderator.created_at.strftime("%m/%d/%Y, %I:%M %p")),
                )
                .replace(
                    "{unix(moderator.created_at)}",
                    str(int(moderator.created_at.timestamp())),
                )
            )
            if isinstance(moderator, Member):
                script_to_resolve = (
                    script_to_resolve.replace(
                        "{moderator.joined_at}",
                        str(moderator.joined_at.strftime("%m/%d/%Y, %I:%M %p")),
                    )
                    .replace(
                        "{unix(moderator.joined_at)}",
                        str(int(moderator.joined_at.timestamp())),
                    )
                    .replace(
                        "{moderator.join_position}",
                        str(
                            sorted(guild.members, key=lambda m: m.joined_at).index(
                                moderator
                            )
                            + 1
                        ),
                    )
                    .replace(
                        "{suffix(moderator.join_position)}",
                        str(
                            ordinal(
                                sorted(guild.members, key=lambda m: m.joined_at).index(
                                    moderator
                                )
                                + 1
                            )
                        ),
                    )
                    .replace(
                        "{moderator.boost}",
                        "Yes" if moderator.premium_since else "No",
                    )
                    .replace(
                        "{moderator.boosted_at}",
                        (
                            str(moderator.premium_since.strftime("%m/%d/%Y, %I:%M %p"))
                            if moderator.premium_since
                            else "Never"
                        ),
                    )
                    .replace(
                        "{unix(moderator.boosted_at)}",
                        (
                            str(int(moderator.premium_since.timestamp()))
                            if moderator.premium_since
                            else "Never"
                        ),
                    )
                    .replace(
                        "{moderator.boost_since}",
                        (
                            str(moderator.premium_since.strftime("%m/%d/%Y, %I:%M %p"))
                            if moderator.premium_since
                            else "Never"
                        ),
                    )
                    .replace(
                        "{unix(moderator.boost_since)}",
                        (
                            str(int(moderator.premium_since.timestamp()))
                            if moderator.premium_since
                            else "Never"
                        ),
                    )
                )

        if case_id := kwargs.get("case_id"):
            script_to_resolve = (
                script_to_resolve.replace("{case.id}", str(case_id))
                .replace("{case}", str(case_id))
                .replace("{case_id}", str(case_id))
            )
        if reason := kwargs.get("reason"):
            script_to_resolve = script_to_resolve.replace("{reason}", str(reason))
        if duration := kwargs.get("duration"):
            script_to_resolve = script_to_resolve.replace("{duration}", str(duration))
        if image := kwargs.get("image"):
            script_to_resolve = script_to_resolve.replace("{image}", str(image))
        if option := kwargs.get("option"):
            script_to_resolve = script_to_resolve.replace("{option}", str(option))
        if text := kwargs.get("text"):
            script_to_resolve = script_to_resolve.replace("{text}", str(text))
        if emoji := kwargs.get("emoji"):
            script_to_resolve = (
                script_to_resolve.replace("{emoji}", str(emoji))
                .replace("{emoji.id}", str(emoji.id))
                .replace("{emoji.name}", str(emoji.name))
                .replace("{emoji.animated}", "Yes" if emoji.animated else "No")
                .replace("{emoji.url}", str(emoji.url))
            )
        if emojis := kwargs.get("emojis"):
            script_to_resolve = script_to_resolve.replace("{emojis}", str(emojis))
        if sticker := kwargs.get("sticker"):
            script_to_resolve = (
                script_to_resolve.replace("{sticker}", str(sticker))
                .replace("{sticker.id}", str(sticker.id))
                .replace("{sticker.name}", str(sticker.name))
                .replace("{sticker.animated}", "Yes" if sticker.animated else "No")
                .replace("{sticker.url}", str(sticker.url))
            )
        if color := kwargs.get("color"):
            script_to_resolve = script_to_resolve.replace(
                "{color}", str(color)
            ).replace("{colour}", str(color))
        if name := kwargs.get("name"):
            script_to_resolve = script_to_resolve.replace("{name}", str(name))
        if "hoist" in kwargs:
            hoist = kwargs.get("hoist")
            script_to_resolve = script_to_resolve.replace(
                "{hoisted}", "Yes" if hoist else "No"
            )
            script_to_resolve = script_to_resolve.replace(
                "{hoist}", "Yes" if hoist else "No"
            )
        if "mentionable" in kwargs:
            mentionable = kwargs.get("mentionable")
            script_to_resolve = script_to_resolve.replace(
                "{mentionable}", "Yes" if mentionable else "No"
            )
        if lastfm := kwargs.get("lastfm"):
            script_to_resolve = (
                script_to_resolve.replace("{lastfm}", lastfm["user"]["name"])
                .replace("{lastfm.name}", lastfm["user"]["name"])
                .replace("{lastfm.url}", lastfm["user"]["url"])
                .replace("{lastfm.avatar}", lastfm["user"]["avatar"] or "")
                .replace(
                    "{lastfm.plays}",
                    comma(lastfm["user"]["library"]["scrobbles"]),
                )
                .replace(
                    "{lastfm.scrobbles}",
                    comma(lastfm["user"]["library"]["scrobbles"]),
                )
                .replace(
                    "{lastfm.library}",
                    comma(lastfm["user"]["library"]["scrobbles"]),
                )
                .replace(
                    "{lastfm.library.artists}",
                    comma(lastfm["user"]["library"]["artists"]),
                )
                .replace(
                    "{lastfm.library.albums}",
                    comma(lastfm["user"]["library"]["albums"]),
                )
                .replace(
                    "{lastfm.library.tracks}",
                    comma(lastfm["user"]["library"]["tracks"]),
                )
                .replace("{artist}", escape_markdown(lastfm["artist"]["name"]))
                .replace("{artist.name}", escape_markdown(lastfm["artist"]["name"]))
                .replace("{artist.url}", lastfm["artist"]["url"])
                .replace("{artist.image}", lastfm["artist"]["image"] or "")
                .replace("{artist.plays}", comma(lastfm["artist"]["plays"]))
                .replace(
                    "{album.cover}",
                    (lastfm["album"]["image"] or "") if lastfm.get("album") else "",
                )
                .replace("{track}", escape_markdown(lastfm["name"]))
                .replace("{track.name}", escape_markdown(lastfm["name"]))
                .replace("{track.url}", lastfm["url"])
                .replace(
                    "{track.image}",
                    lastfm["image"]["url"] if lastfm["image"] else "",
                )
                .replace(
                    "{track.cover}",
                    lastfm["image"]["url"] if lastfm["image"] else "",
                )
                .replace("{track.plays}", comma(lastfm["plays"]))
                .replace(
                    "{lower(artist)}",
                    escape_markdown(lastfm["artist"]["name"].lower()),
                )
                .replace(
                    "{lower(artist.name)}",
                    escape_markdown(lastfm["artist"]["name"].lower()),
                )
                .replace(
                    "{lower(album)}",
                    (
                        escape_markdown(lastfm["album"]["name"].lower())
                        if lastfm.get("album")
                        else ""
                    ),
                )
                .replace(
                    "{lower(album.name)}",
                    (
                        escape_markdown(lastfm["album"]["name"].lower())
                        if lastfm.get("album")
                        else ""
                    ),
                )
                .replace("{lower(track)}", escape_markdown(lastfm["name"].lower()))
                .replace(
                    "{lower(track.name)}",
                    escape_markdown(lastfm["name"].lower()),
                )
                .replace(
                    "{upper(artist)}",
                    escape_markdown(lastfm["artist"]["name"].upper()),
                )
                .replace(
                    "{upper(artist.name)}",
                    escape_markdown(lastfm["artist"]["name"].upper()),
                )
                .replace(
                    "{upper(album)}",
                    (
                        escape_markdown(lastfm["album"]["name"].upper())
                        if lastfm.get("album")
                        else ""
                    ),
                )
                .replace(
                    "{upper(album.name)}",
                    (
                        escape_markdown(lastfm["album"]["name"].upper())
                        if lastfm.get("album")
                        else ""
                    ),
                )
                .replace("{upper(track)}", escape_markdown(lastfm["name"].upper()))
                .replace(
                    "{upper(track.name)}",
                    escape_markdown(lastfm["name"].upper()),
                )
                .replace(
                    "{title(artist)}",
                    escape_markdown(lastfm["artist"]["name"].title()),
                )
                .replace(
                    "{title(artist.name)}",
                    escape_markdown(lastfm["artist"]["name"].title()),
                )
                .replace(
                    "{title(album)}",
                    (
                        escape_markdown(lastfm["album"]["name"].title())
                        if lastfm.get("album")
                        else ""
                    ),
                )
                .replace(
                    "{title(album.name)}",
                    (
                        escape_markdown(lastfm["album"]["name"].title())
                        if lastfm.get("album")
                        else ""
                    ),
                )
                .replace("{title(track)}", escape_markdown(lastfm["name"].title()))
                .replace(
                    "{title(track.name)}",
                    escape_markdown(lastfm["name"].title()),
                )
            )
            if lastfm["artist"].get("crown"):
                script_to_resolve = script_to_resolve.replace("{artist.crown}", "👑")
            else:
                script_to_resolve = script_to_resolve.replace(
                    "`{artist.crown}`", ""
                ).replace("{artist.crown}", "")

        # If we're resolving the instance script, update it
        if script is None:
            self.script = script_to_resolve

        return script_to_resolve

    async def resolve_objects(self, **kwargs):
        """Attempt to resolve the objects in the script"""
        # No need to re-register tags if already registered
        if self.parser.tags and self.embed_parser.tags:
            return

        # Register main parser methods
        self.register_parser_methods()

        # Register embed parser methods
        self.register_embed_parser_methods()

        # **Removed 'context=kwargs' from parse method call**
        # Parse the main script
        await self.parser.parse(self.script)

    async def compile(self, **kwargs):
        """Attempt to compile the script into an object"""
        # If we've already compiled and we're just validating, return early
        if kwargs.get("validate") and self.objects.get("embeds"):
            self._type = "embed"
            return True

        # Store original script before variable resolution
        original_script = self.script

        # Resolve variables first
        self.script = await self.resolve_variables(**kwargs)
        await self.resolve_objects(**kwargs)

        try:
            # Initialize button list if not exists
            if "button" not in self.objects:
                self.objects["button"] = []

            # **Remove 'context=kwargs' from parse call**
            # First process buttons and other non-embed components with main parser
            parsed_script = await self.parser.parse(
                self.script
            )  # Removed context=kwargs
            self.script = parsed_script.replace(
                "\\n", "\n"
            )  # Convert escaped newlines back to actual newlines

            # Then process embed components
            for embed_script in parsed_script.split("{embed}"):
                if embed_script := embed_script.strip():
                    self.objects["embed"] = Embed()
                    # Resolve variables again for each embed component
                    embed_script = await self.resolve_variables(
                        script=embed_script, **kwargs
                    )
                    # Then split by $v to handle embed components
                    for component in embed_script.split("$v"):
                        if component := component.strip():
                            # Resolve variables one more time for each component
                            component = await self.resolve_variables(
                                script=component, **kwargs
                            )
                            await self.embed_parser.parse(
                                component.replace("\\n", "\n")
                            )
                    if embed := self.objects.pop("embed", None):
                        self.objects["embeds"].append(embed)
            self.objects.pop("embed", None)

        except Exception as error:
            # Restore original script in case of error
            self.script = original_script

            if kwargs.get("validate"):
                if isinstance(error, TypeError):
                    function = [
                        tag.name
                        for tag in self.embed_parser.tags.values()
                        if tag.callback.__name__ == error.args[0].split("(")[0]
                    ]
                    function = function[0] if function else "Unknown"
                    parameters = str(error).split("'")[1].split(", ")
                    raise CommandError(
                        f"The **{function}** method requires the `{parameters[0]}` parameter"
                    ) from error
                raise error

        validation = any(self.objects.values())
        if not validation:
            self.objects["content"] = self.script
        return validation

    async def send(self, bound: TextChannel, **kwargs):
        """Attempt to send the embed to the channel"""
        try:
            # Resolve variables and compile
            await self.resolve_variables(**kwargs)
            if not self.objects.get("embeds"):
                await self.compile(**kwargs)

            # Resolve variables in content if present
            if self.objects.get("content"):
                self.objects["content"] = await self.resolve_variables(
                    script=self.objects["content"], **kwargs
                )

            # Handle buttons if present
            if button := self.objects.pop("button", None):
                self.objects["view"] = LinkView(
                    links=[LinkButton(**data) for data in button]
                )
            # Add any additional kwargs for message sending
            for key, value in kwargs.items():
                if key in ["delete_after", "allowed_mentions", "reference"]:
                    self.objects[key] = value

            # Handle webhook-specific ephemeral messages
            if isinstance(bound, Webhook) and (ephemeral := kwargs.get("ephemeral")):
                self.objects["ephemeral"] = ephemeral

            # Determine whether to edit or send based on bound type
            method = "edit" if isinstance(bound, Message) else "send"

            # Make sure embeds have variables resolved
            if self.objects.get("embeds"):
                for embed in self.objects["embeds"]:
                    if embed.description:
                        embed.description = await self.resolve_variables(
                            script=embed.description, **kwargs
                        )
                    if embed.title:
                        embed.title = await self.resolve_variables(
                            script=embed.title, **kwargs
                        )

            # Send/edit the message with all compiled objects
            return await getattr(bound, method)(**self.objects)

        except Exception as e:
            print(f"Error in send method: {e}")
            raise

    def replace(self, key: str, value: str):
        """Replace a key word in the script"""
        self.script = self.script.replace(key, value)
        return self

    def strip(self):
        """Strip the script"""
        self.script = self.script.strip()
        return self

    def type(self, suffix: bool = True, bold: bool = True):
        """Return the script type"""
        if self._type == "embed":
            return (
                "embed"
                if not suffix
                else "an **embed message**" if bold else "an embed"
            )
        return "text" if not suffix else "a **text message**" if bold else "a text"

    def __str__(self):
        return self.script

    def __repr__(self):
        return f"<length={len(self.script)}>"


class EmbedScriptValidator(Converter):
    @staticmethod
    async def convert(ctx: Context, argument: str):
        script = EmbedScript(argument)
        await script.compile(validate=True)
        return script
