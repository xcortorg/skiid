from typing import Any, Union, Dict, Optional
import discord, asyncio, re, datetime, aiohttp
from discord.ext import commands
from discord import Thread, TextChannel
from discord.ext.commands import CommandError, Context
import TagScriptEngine as tse
from TagScriptEngine import Verb as String


def embed_to_code(
    embed: Union[dict, discord.Message, discord.Embed],
    message: Optional[str] = None,
    escaped: Optional[bool] = True,
) -> dict:
    """Converts an embed to a code block."""
    code = "{embed}"
    msg = None
    if isinstance(embed, dict):
        message = embed.pop("message", embed.pop("content", message))
        embed = discord.Embed.from_dict(embed)
    elif isinstance(embed, discord.Message):
        msg = embed
        message = message or str(embed.content)
        embed = embed.embeds[0]
    if msg:
        for component in msg.components:
            if isinstance(component, (discord.Button, discord.components.Button)):
                if component.url:
                    substeps = "$v{button: "
                    if component.label:
                        substeps += f"{component.label} && "
                    if component.emoji:
                        substeps += f"{str(component.emoji)} && "
                    substeps += f"{component.url}}}"
                    code += substeps
            elif isinstance(component, discord.ActionRow):
                for child in component.children:
                    if isinstance(child, (discord.Button, discord.components.Button)):
                        if child.url:
                            substeps = "$v{button: "
                            if child.label:
                                substeps += f"{child.label} && "
                            if child.emoji:
                                substeps += f"{str(child.emoji)} && "
                            substeps += f"{child.url}}}"
                            code += substeps

    if message:
        code += f"$v{{content: {message}}}"
    if embed.title:
        code += f"$v{{title: {embed.title}}}"
    if embed.description:
        code += f"$v{{description: {embed.description}}}"
    if embed.timestamp:
        code += "$v{timestamp: true}"
    if embed.url:
        code += f"$v{{url: {embed.url}}}"
    if fields := embed.fields:
        for field in fields:
            inline = " && inline" if field.inline else ""
            code += f"$v{{field: {field.name} && {field.value}{inline}}}"
    if embed.footer:
        substeps = ""
        text = embed.footer.text or ""
        icon_url = embed.footer.icon_url or ""
        substeps += f"footer: {embed.footer.text}"
        if icon_url:
            substeps += f" && {icon_url}"
        code += f"$v{{{substeps}}}"
    if embed.author:
        substeps = ""
        icon_url = embed.author.icon_url or ""
        url = embed.author.url or None
        substeps += f"author: {embed.author.name}"
        if url:
            substeps += f" && {url}"
        if icon_url:
            substeps += f" && {icon_url}"
        code += "$v{" + substeps + "}"
    if image_url := embed.image.url:
        code += f"$v{{image: {image_url}}}"
    if thumbnail_url := embed.thumbnail.url:
        code += f"$v{{thumbnail: {thumbnail_url}}}"
    if color := embed.color:
        code += f"$v{{color: #{str(color)}}}".replace("##", "#")
    if escaped:
        code = code.replace("```", "`\u200b`\u200b`")
    return code


def format_plays(amount):
    if amount == 1:
        return "play"
    return "plays"


def ordinal(n):
    n = int(n)
    return "%d%s" % (n, "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10 :: 4])


ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}

# URL pattern to verify the format
URL_PATTERN = re.compile(
    r"^(https?://)"
    r"([a-zA-Z0-9.-]+)"  # Domain
    r"(\.[a-zA-Z]{2,})"  # TLD
    r"(/.*)?$",  # Path
)


async def is_valid_icon_url(url: str) -> bool:
    # Check if URL format is valid
    if not URL_PATTERN.match(url):
        return False

    # Check the Content-Type to ensure it's an allowed image format
    async with aiohttp.ClientSession() as session:
        try:
            async with session.head(url) as response:
                content_type = response.headers.get("Content-Type", "")
                return content_type in ALLOWED_MIME_TYPES
        except Exception as e:
            print(f"Failed to fetch URL: {e}")
            return False


async def to_embedcode(data: str) -> str:
    data = data.replace("```", "`` `")
    return f"``` {data} ```"


async def to_embedcode_escaped(data: str) -> str:
    return discord.utils.escape_markdown(data)


class FormatError(Exception):
    def __init__(self, message: str):
        self.message = message
        return super().__init__(message)


class InvalidEmbed(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def link_validation(string: str):
    regex = r"((http(s)?(\:\/\/))+(www\.)?([\w\-\.\/])*(\.[a-zA-Z]{2,3}\/?))[^\s\b\n|]*[^.,;:\?\!\@\^\$ -]"
    results = re.findall(regex, string)
    if len(results) == 0:
        return False
    else:
        return True


def get_amount(amount: Union[int, str], limit: int):
    if isinstance(amount, int):
        return limit - amount
    else:
        return limit - len(amount)


async def validate_images(url: str, type: str):
    url = (
        f"https://proxy.rival.rocks?url={url}"
        if "discordapp.com" not in url or "discord.com" not in url
        else url
    )
    try:
        async with aiohttp.ClientSession() as session:
            async with session.request("HEAD", url) as req:
                if (
                    "image" in req.headers["Content-Type"].lower()
                    and int(req.headers.get("Content-Length", 50000)) < 50000000
                ):
                    return True
                else:
                    raise InvalidEmbed(f"Image URL {url} is invalid")
    except Exception as e:
        raise InvalidEmbed(f"{type.lower().title()} URL {url} is invalid")


async def validator(data: dict):
    for k, v in data.items():
        k = k.lower()
        if k in ("image", "thumbnail"):
            if v in ["", "", None, "None", "None", "none"]:
                data.pop(k)
            else:
                # 				await validate_images(v,k)
                if link_validation(v["url"]) is False:
                    raise InvalidEmbed(f'Embed {k} URL is not a valid URL `{v["url"]}`')
        if k == "url":
            c = link_validation(v)
            if c is False:
                raise InvalidEmbed("Embed URL isnt a valid URL")
        if k == "title":
            if len(v) >= 256:
                raise InvalidEmbed(f"title is too long (`{get_amount(v,256)}`)")
        if k == "description":
            if len(v) >= 4096:
                raise InvalidEmbed(f"description is too long (`{get_amount(v,4096)}`)")
        if k == "author":
            if len(v.get("name", "")) >= 256:
                raise InvalidEmbed(
                    f"author name is too long (`{get_amount(v['name'],256)}`)"
                )
            if v.get("icon_url"):
                if v["icon_url"] in ["", "", None, "None", "None", "none"]:
                    v.pop("icon_url")
                else:
                    c = link_validation(v["icon_url"])
                    if c is False:
                        raise InvalidEmbed("Author Icon Isnt a valid URL")
                    # await validate_images(v,'icon_url')
        if k == "fields":
            for f in v:
                i = v.index(f)
                if len(f["name"]) >= 256:
                    raise InvalidEmbed(
                        f"field {i+1}'s name is too long (`{get_amount(f['name'],256)}`)"
                    )
                if len(f["value"]) >= 1024:
                    raise InvalidEmbed(
                        f"field {i+1}'s value is too long (`{get_amount(f['value'],1024)}`)"
                    )
        if k == "footer":
            if len(v.get("text", "")) >= 2048:
                raise InvalidEmbed(
                    f"footer text is too long (`{get_amount(v['text'],2048)}`)"
                )
            if v.get("icon_url"):
                if v["icon_url"] in ["", "", None, "None", "None", "none"]:
                    v.pop("icon_url")
                else:
                    if link_validation(v.get("icon_url")) is False:
                        raise InvalidEmbed("Footer Icon URL is not a valid URL")
                    # await validate_images(v['icon_url'],'icon_url')
    if len(discord.Embed.from_dict(data)) >= 6000:
        raise InvalidEmbed(
            f"Embed is too long (`{get_amount(len(discord.Embed.from_dict(data)),6000)}`)"
        )
    return True


async def m(d: str, sendable: bool = False):
    d = str(d)
    d = d.replace("{embed}", "")
    o = {}
    final = {}
    author = None
    e = discord.Embed()
    view = discord.ui.View()
    final["view"] = view
    if d.startswith("$v"):
        d = d[2:]
    if d.endswith("$v"):
        d = d[: len(d) - 2]
    data = d.split("$v")
    for string_check in data:
        if "}{" in string_check:
            raise FormatError(f"Missing `$v` between `}}{{`")
        if not str(string_check).startswith("{"):
            raise FormatError(f"Missing `{{` in portion of embed `{string_check}`")
        if not str(string_check).endswith("}"):
            raise FormatError(f"Missing `}}` in portion of embed `{string_check}`")
    o["fields"] = []
    for s in data:
        pr = String(s)
        k = pr.declaration
        if pr.payload == None:
            return {"content": k}
        pay = pr.payload.lstrip().rstrip()
        if pay and " && " in pay:
            meow = {}
            py = pay.split(" && ")
            if k.lower() in ("field", "footer", "label", "author"):
                if k.lower() == "footer":
                    meow["text"] = py[0]
                    meow["icon"] = py[1].replace("icon: ", "")
                if k.lower() == "label":
                    view.add_item(
                        discord.ui.Button(
                            label=py[0], url=py[1].strip("link:").lstrip().rstrip()
                        )
                    )
                if k.lower() == "field":
                    meo = {}
                    meo["name"] = py[0]
                    meo["value"] = py[1].replace("value:", "")
                    if len(py) == 3:
                        meo["inline"] = bool(py[2].replace("inline:", "").strip())
                    o["fields"].append(meo)
                if k.lower() == "author" or k.lower() == "uthor":
                    meo = {"name": py[0]}
                    # 					print(py)
                    py.remove(py[0])
                    for t in py:
                        t = t.lstrip().rstrip()
                        if ":" in t:
                            if "icon:" in t:
                                icon = t.replace("icon:", "")
                                if link_validation(icon) is not False:
                                    meo["icon_url"] = icon
                                else:
                                    raise InvalidEmbed(
                                        message="Author Icon URL is an Invalid URL"
                                    )
                            else:
                                url = t.replace("url:", "")
                                if link_validation(url) is not False:
                                    meo["url"] = url
                                else:
                                    raise InvalidEmbed(
                                        message="Author URL is an Invalid URL"
                                    )
                    # 					print(meo)
                    o["author"] = meo
                    author = meo
            else:
                for t in py:
                    if ":" in t:
                        parts = t.split(":", 1)
                        meow[parts[0].strip()] = parts[1]
                    else:
                        o[k] = t
            o[k] = meow
        else:
            if k.lower() == "content" or k.lower() == "autodelete":
                final[k] = pay
            elif k.lower() == "author" or k.lower() == "url":
                if k.lower() == "url":
                    if link_validation(pay) is False:
                        raise InvalidEmbed(message=f"Embed URL is an Invalid URL")
                else:
                    o["author"] = {"name": pay}
            else:
                if k.lower() == "timestamp":
                    o["timestamp"] = datetime.datetime.now().isoformat()
                else:
                    o[k] = pay
    if o.get("author") == {} and author is not None:
        o["author"] = author
    final["embed"] = o
    if final["embed"].get("thumbnail"):
        if link_validation(final["embed"].get("thumbnail")) is False:
            raise InvalidEmbed(
                message=f"Thumbnail URL is an Invalid URL {final['embed']['thumbnail']}"
            )
        else:
            th = {"url": final["embed"]["thumbnail"]}
            final["embed"]["thumbnail"] = th
    if final["embed"].get("image"):
        if link_validation(final["embed"].get("image")) is False:
            raise InvalidEmbed(message="Image URL is an Invalid URL")
        else:
            th = {"url": final["embed"]["image"]}
            final["embed"]["image"] = th
    # 	if not final['embed'].get('description') and not final['embed'].get('title') and not len(final['embed'].get('fields',[])) > 0 and not final['embed'].get('image') and not final['embed'].get('thumbnail'):
    # 		raise InvalidEmbed(message='A description,title,image,thumbnail or field is required')
    if final["embed"].get("footer"):
        if isinstance(final["embed"]["footer"], str):
            final["embed"]["footer"] = {"text": final["embed"]["footer"]}
        if final["embed"]["footer"].get("icon"):
            if final["embed"]["footer"]["icon"].startswith("icon: "):
                final["embed"]["footer"]["icon_url"] = final["embed"]["footer"][
                    "icon"
                ].strip("icon: ")
            else:
                final["embed"]["footer"]["icon_url"] = final["embed"]["footer"]["icon"]
            try:
                final["embed"]["footer"].pop("icon")
            except Exception:
                pass
    if final["embed"].get("author"):
        if final["embed"]["author"].get("icon"):
            # 			print(final['embed']['author'])
            final["embed"]["author"]["icon_url"] = (
                final["embed"]["author"].get("icon").strip(" icon: ")
            )
            try:
                final["embed"]["author"].pop("icon")
            except Exception:
                pass
    if final["embed"].get("uthor"):
        # 		print(final['embed']['uthor'])
        final["embed"]["author"] = final["embed"]["uthor"]
        final["embed"]["author"]["icon_url"] = final["embed"]["author"].get(
            "icon", None
        )
        try:
            final["embed"]["author"].pop("icon")
        except Exception:
            pass
        final["embed"].pop("uthor")
    if final.get("autodelete"):
        final["delete_after"] = int(final["autodelete"])
        final.pop("autodelete")
    if final["embed"].get("color"):
        color = final["embed"]["color"]
        if color.endswith("}") and "{" not in color:
            color = color[: len(color) - 2]
        # 		color=final['embed']['color']
        if not color.startswith("#"):
            try:
                final["embed"]["color"] = discord.Color(value=int(color))
            except Exception:
                color = f"#{color}"
        try:
            final["embed"]["color"] = int(discord.Color.from_str(color))
        except Exception as e:
            final["error"] = f"{str(e)} ({final['embed']['color']})"
            final["embed"]["color"] = 0x000001
    try:
        final["embed"].pop("field")
    except Exception:
        pass
    try:
        final["embed"].pop("label")
    except Exception:
        pass
    if len(final["embed"]) == 0:
        final.pop("embed")
    if final.get("embed"):
        if len(final["embed"].get("fields", [])) == 0:
            final["embed"].pop("fields")
        await validator(final["embed"])
    # 	if not final['embed'].get('image') and not final['embed'].get('thumbnail') and final['embed'].get('fields',[]) == []:
    # 		if final['embed'].get('author') or final['embed'].get('footer'):
    # 			if not final['embed'].get('description'): raise InvalidEmbed(f'Either a Thumbnail,Image,Description, Or Fields are Required')
    # 	if final.get('embed'):
    # 		if not final['embed'].get('color'): final['embed']['color']=int(discord.Color(value=0))
    if len(final.get("embed", {})) == 0:
        try:
            final.pop("embed")
        except Exception:
            pass
    if sendable is True:
        if final.get("embed"):
            final["embed"] = discord.Embed.from_dict(final["embed"])
    return final


class Script:

    def __init__(
        self,
        template: str,
        user: Union[discord.Member, discord.User],
        lastfm_data: dict = {},
    ):
        self.data: Dict[str, Union[Dict, str]] = {
            "embed": {},
        }
        self.replacements = {
            "{user}": str(user),
            "{user.mention}": user.mention,
            "{user.name}": user.name,
            "{user.avatar}": user.display_avatar.url,
            "{user.joined_at}": discord.utils.format_dt(user.joined_at, style="R"),
            "{user.created_at}": discord.utils.format_dt(user.created_at, style="R"),
            "{guild.name}": user.guild.name,
            "{guild.count}": str(user.guild.member_count),
            "{guild.count.format}": ordinal(len(user.guild.members)),
            "{guild.id}": user.guild.id,
            "{guild.created_at}": discord.utils.format_dt(
                user.guild.created_at, style="R"
            ),
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
            "{whitespace}": "\u200e",
        }
        self.template = self._replace_placeholders(
            template.replace("`\u200b`\u200b`", "```")
            .replace(r"\n", "\n")
            .replace("\\n", "\n")
        )

    def _replace_placeholders(self, template: str) -> str:
        template = (
            template.replace("{embed}", "").replace("$v", "").replace("} {", "}{")
        )
        for placeholder, value in self.replacements.items():
            template = template.replace(placeholder, str(value))
        return template

    def __str__(self) -> str:
        return self.template

    async def data(self, sendable: bool = False) -> dict:
        return await m(self.template, sendable)

    async def send(
        self, channel: Union[TextChannel, Thread, discord.Message], **kwargs: Any
    ) -> discord.Message:
        if isinstance(channel, (TextChannel, Thread)):
            return await channel.send(await m(self.template, True), **kwargs)
        else:
            return await channel.edit(await m(self.template, True), **kwargs)

    async def compile(self):
        await m(self.template)
        return True

    @classmethod
    async def convert(cls, ctx: Context, template: str):
        script = cls(template, ctx.author)
        await script.compile()
        return script.__str__()
