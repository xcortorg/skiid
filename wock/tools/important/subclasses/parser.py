from re import DOTALL, Match, compile, sub  # noqa: F401
from typing import Any, Callable, Dict, Optional, Union

from aiohttp import ClientSession
from discord import (ButtonStyle, Embed, Guild, Member, Message,  # noqa: F401
                     User)
from discord.abc import GuildChannel
from discord.ext.commands import CommandError, Context, Converter
from discord.ui import Button, View
from discord.utils import format_dt
from typing_extensions import NoReturn, Self, Type

image_link = compile(
    r"https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&\/\/=]*(?:\.png|\.jpe?g|\.gif|\.jpg|))"
)


def ordinal(n):
    n = int(n)
    return "%d%s" % (n, "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10 :: 4])


class EmbedConverter(Converter):
    async def convert(self, ctx: Context, code: str) -> Optional[dict]:
        script = Script(code, ctx.author)
        try:
            await script.compile()
        except EmbedError as e:
            await ctx.warning(f"{e.message}")
            raise e
        return await script.send(ctx.channel, return_embed=True)


class EmbedError(CommandError):
    def __init__(self, message: str, **kwargs):
        self.message = message
        super().__init__(message, kwargs)


class Script:
    def __init__(self, template: str, user: Member | User, lastfm_data: dict = {}):
        self.pattern = compile(r"\{([\s\S]*?)\}")  # compile(r"{(.*?)}")
        self.data: Dict[str, Union[Dict, str]] = {
            "embed": {},
        }
        self.replacements = {
            "{user}": str(user),
            "{user.mention}": user.mention,
            "{user.name}": user.name,
            "{user.avatar}": user.display_avatar.url,
            "{user.joined_at}": format_dt(user.joined_at, style="R"),
            "{user.created_at}": format_dt(user.created_at, style="R"),
            "{guild.name}": user.guild.name,
            "{guild.count}": str(user.guild.member_count),
            "{guild.count.format}": ordinal(len(user.guild.members)),
            "{guild.id}": user.guild.id,
            "{guild.created_at}": format_dt(user.guild.created_at, style="R"),
            "{guild.boost_count}": str(user.guild.premium_subscription_count),
            "{guild.booster_count}": str(len(user.guild.premium_subscribers)),
            "{guild.boost_count.format}": ordinal(
                str(user.guild.premium_subscription_count)
            ),
            "{guild.booster_count.format}": ordinal(
                str(user.guild.premium_subscription_count)
            ),
            "{guild.boost_tier}": str(user.guild.premium_tier),
            "{guild.icon}": user.guild.icon.url if user.guild.icon else "",
            "{track}": lastfm_data.get("track", ""),
            "{track.duration}": lastfm_data.get("duration", ""),
            "{artist}": lastfm_data.get("artist", ""),
            "{user}": lastfm_data.get("user", ""),  # noqa: F601
            "{avatar}": lastfm_data.get("avatar", ""),
            "{track.url}": lastfm_data.get("track.url", ""),
            "{artist.url}": lastfm_data.get("artist.url", ""),
            "{scrobbles}": lastfm_data.get("scrobbles", ""),
            "{track.image}": lastfm_data.get("track.image", ""),
            "{username}": lastfm_data.get("username", ""),
            "{artist.plays}": lastfm_data.get("artist.plays", ""),
            "{track.plays}": lastfm_data.get("track.plays", ""),
            "{track.lower}": lastfm_data.get("track.lower", ""),
            "{artist.lower}": lastfm_data.get("artist.lower", ""),
            "{track.hyperlink}": lastfm_data.get("track.hyperlink", ""),
            "{track.hyperlink_bold}": lastfm_data.get("track.hyperlink_bold", ""),
            "{artist.hyperlink}": lastfm_data.get("artist.hyperlink", ""),
            "{artist.hyperlink_bold}": lastfm_data.get("artist.hyperlink_bold", ""),
            "{track.color}": lastfm_data.get("track.color", ""),
            "{artist.color}": lastfm_data.get("artist.color", ""),
            "{date}": lastfm_data.get("date", ""),
        }
        self.template = self._replace_placeholders(template)

    def get_color(self, color: str):
        try:
            return int(color, 16)
        except Exception:
            raise EmbedError(f"color `{color[:6]}` not a valid hex color")

    @property
    def components(self) -> Dict[str, Callable[[Any], None]]:
        return {
            "content": lambda value: self.data.update({"content": value}),
            "autodelete": lambda value: self.data.update({"delete_after": int(value)}),
            "url": lambda value: self.data["embed"].update({"url": value}),
            "color": lambda value: self.data["embed"].update(
                {"color": self.get_color(value.replace("#", ""))}
            ),
            "title": lambda value: self.data["embed"].update({"title": value}),
            "description": (
                lambda value: self.data["embed"].update({"description": value})
            ),
            "thumbnail": (
                lambda value: self.data["embed"].update({"thumbnail": {"url": value}})
            ),
            "fields": (lambda value: self.data["embed"].update({"fields": value})),
            "image": (
                lambda value: self.data["embed"].update({"image": {"url": value}})
            ),
            "footer": (
                lambda value: self.data["embed"]
                .setdefault("footer", {})
                .update({"text": value})
            ),
            "author": (
                lambda value: self.data["embed"]
                .setdefault("author", {})
                .update({"name": value})
            ),
        }

    # def parse_variable(self, match: Match) -> str:
    #     name = match.group(1)
    #     value = self.variables

    #     try:
    #         for attr in name.split("."):
    #             value = value[attr]

    #         return str(value)
    #     except (AttributeError, TypeError, KeyError):
    #         return match.group(1)

    def validate_keys(self: Self):
        data = self.template.split("{")
        for d in data:
            if d != "":
                if not d.endswith("}") and not d.endswith("$v"):
                    missing = "}"
                    raise EmbedError(
                        f"`{d.split(':')[0]}` is missing a `{missing}` at the end"
                    )
        _data = self.template.split("}")
        for _d in _data:
            if _d != "":
                if not _d.startswith("{") and not d.startswith("$v{"):
                    missing = "{"
                    raise EmbedError(
                        f"`{_d.split(':')[0]}` is missing a `{missing}` at the start"
                    )

    def validate_url(self: Self, url: str) -> Optional[bool]:
        import re

        regex_pattern = r"^https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+.*$"
        data = bool(re.match(regex_pattern, url))
        if not data:
            raise EmbedError(f"`{url}` is not a valid URL Format")
        return data

    async def validate_image(self: Self, url: str) -> Optional[bool]:
        if not image_link.match(url):
            raise EmbedError(f" 1 `{url}` is not a valid Image URL Format")
        async with ClientSession() as session:
            async with session.request("HEAD", url) as response:
                if int(response.headers.get("Content-Length", 15000)) > 240000000:
                    raise EmbedError(f"`{url}` is to large of a URL")
                if content_type := response.headers.get("Content-Type"):
                    if "image" not in content_type.lower():
                        raise EmbedError(
                            f"`{url}` is not a valid Image URL due to the content type being `{content_type}`"
                        )
                else:
                    raise EmbedError(f"`{url}` is not a valid Image URL")
        return True

    async def validate(self: Self) -> NoReturn:
        DICT = {}
        if thumbnail := self.data.get("embed").get("thumbnail", DICT).get("url"):
            await self.validate_image(thumbnail)
        if image := self.data.get("embed").get("image", DICT).get("url"):
            await self.validate_image(image)
        if author_icon := self.data.get("embed").get("author", DICT).get("icon_url"):
            await self.validate_image(author_icon)
        if footer_icon := self.data.get("embed").get("footer", DICT).get("icon_url"):
            await self.validate_image(footer_icon)
        if author_url := self.data.get("embed").get("author", DICT).get("url"):
            self.validate_url(author_url)
        if embed_url := self.data.get("embed").get("url"):
            self.validate_url(embed_url)
        author = self.data.get("embed").get("author", DICT).get("name", "")
        footer = self.data.get("embed").get("footer", DICT).get("text", "")
        title = self.data.get("embed").get("title", "")
        description = self.data.get("embed").get("description", "")
        fields = self.data.get("embed").get("fields", [])
        if len(author) >= 256:
            raise EmbedError(
                "field `author name` is to long the limit is 256 characters"
            )
        if len(footer) >= 2048:
            raise EmbedError(
                "field `footer text` is to long the limit is 2048 characters"
            )
        if len(description) >= 4096:
            raise EmbedError(
                "field `description` is to long the limit is 4096 characters"
            )
        for f in fields:
            if len(f.get("name", "")) >= 256:
                raise EmbedError("field `name` is to long the limit is 256 characters")
            if len(f.get("value", "")) >= 1024:
                raise EmbedError(
                    "field `value` is to long the limit is 1024 characters"
                )
        if len(title) >= 256:
            raise EmbedError("field `title` is to long the limit is 256 characters")
        if len(self.data.get("content", "")) >= 2000:
            raise EmbedError("field `content` is to long the limit is 2000 characters")
        if len(Embed.from_dict(self.data["embed"])) >= 6000:
            raise EmbedError("field `embed` is to long the limit is 6000 characters")

    def _replace_placeholders(self: Self, template: str) -> str:
        template = (
            template.replace("{embed}", "").replace("$v", "").replace("} {", "}{")
        )
        for placeholder, value in self.replacements.items():
            template = template.replace(placeholder, str(value))
        return template

    async def compile(self: Self) -> None:
        self.template = self.template.replace(r"\n", "\n").replace("\\n", "\n")
        matches = self.pattern.findall(self.template)

        for match in matches:
            parts = match.split(":", 1)
            if len(parts) == 2:
                if parts[0] == "footer" and "&&" in parts[1]:
                    values = parts[1].split("&&")
                    for i, v in enumerate(values, start=1):
                        if i == 1:
                            self.data["embed"]["footer"] = {"text": v.lstrip().rstrip()}
                        elif i == 2:
                            self.data["embed"]["footer"]["url"] = v.lstrip().rstrip()
                        else:
                            self.data["embed"]["footer"][
                                "icon_url"
                            ] = v.lstrip().rstrip()
                elif parts[0] == "author" and "&&" in parts[1]:
                    values = parts[1].split("&&")
                    for i, v in enumerate(values, start=1):
                        if i == 1:
                            self.data["embed"]["author"] = {"name": v.lstrip().rstrip()}
                        elif i == 2:
                            if (
                                ".jpg" in v.lstrip().rstrip()
                                or ".png" in v.lstrip().rstrip()
                                or ".gif" in v.lstrip().rstrip()
                                or ".webp" in v.lstrip().rstrip()
                            ):
                                self.data["embed"]["author"][
                                    "icon_url"
                                ] = v.lstrip().rstrip()
                            else:
                                self.data["embed"]["author"][
                                    "url"
                                ] = v.lstrip().rstrip()
                        else:
                            self.data["embed"]["author"][
                                "icon_url"
                            ] = v.lstrip().rstrip()
                elif parts[0] == "button":
                    button_data = parts[1].split("&&")
                    if len(button_data) >= 2:
                        button_label = button_data[0].strip()
                        _button_url = (
                            button_data[1].strip().replace("url: ", "").replace(" ", "")
                        )
                        self.validate_url(_button_url)
                        if not self.data.get("button"):
                            self.data["button"] = {
                                "label": button_label,
                                "url": _button_url,
                            }
                elif parts[0] == "field":
                    if "fields" not in self.data["embed"]:
                        self.data["embed"]["fields"] = []
                    field_data = parts[1].split("&&")
                    field_name = field_data[0].strip()
                    field_value = None
                    inline = False

                    if len(field_data) >= 2:
                        field_value = (
                            field_data[1].strip().replace("value: ", "") or None
                        )

                    if len(field_data) >= 3:
                        inline = bool(field_data[2].strip().replace("inline ", ""))

                    self.data["embed"]["fields"].append(
                        {"name": field_name, "value": field_value, "inline": inline}
                    )
                else:
                    name, value = map(str.strip, parts)
                    if name not in self.components:
                        continue

                    self.components[name](value)

        if self.template.startswith("{"):
            self.validate_keys()
            await self.validate()
        else:
            self.data.pop("embed", None)
            self.data["content"] = self.template

    async def send(self: Self, target: Context | GuildChannel, **kwargs) -> Message:
        button = self.data.pop("button", None)
        if button:
            view = View()
            view.add_item(
                Button(
                    style=ButtonStyle.link,
                    label=button["label"],
                    url=button["url"],
                )
            )
            kwargs["view"] = view
        else:
            if kwargs.get("view"):
                pass
            else:
                kwargs["view"] = None
        if isinstance(self.data.get("embed"), Embed):
            embed = self.data["embed"]
        else:
            embed = (
                Embed.from_dict(self.data["embed"]) if self.data.get("embed") else None
            )
        if embed:
            kwargs["embed"] = embed
        if content := self.data.get("content"):
            kwargs["content"] = content
        if delete_after := self.data.get("delete_after"):
            kwargs["delete_after"] = delete_after
        if kwargs.pop("return_embed", False):
            return kwargs
        return await target.send(
            **kwargs,
        )

    @classmethod
    async def convert(cls: Type["Script"], ctx: Context, argument: str) -> "Script":
        data = cls(template=argument, user=ctx.author)
        await data.compile()
        return data

    def __repr__(self: Self) -> str:
        return f"<Parser template={self.template!r}>"

    def __str__(self: Self) -> str:
        return self.template


# type: ignore
