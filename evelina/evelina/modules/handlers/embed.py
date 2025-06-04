import re
import discord
import datetime

from discord.ext import commands

class EmbedBuilder:
    def __init__(self):
        self.ok = "hi"

    def ordinal(self, num: int) -> str:
        numb = str(num)
        if numb.startswith("0"):
            numb = numb.strip("0")
        if numb in ["11", "12", "13"]:
            return numb + "th"
        if numb.endswith("1"):
            return numb + "st"
        elif numb.endswith("2"):
            return numb + "nd"
        elif numb.endswith("3"):
            return numb + "rd"
        else:
            return numb + "th"

    def embed_replacement(self, user: discord.Member, params: str = None):
        if params is None:
            return None
        if user is None:
            return None
        if "{user}" in params:
            params = params.replace("{user}", str(user))
        if "{user.id}" in params:
            params = params.replace("{user.id}", str(user.id))
        if "{user.name}" in params:
            params = params.replace("{user.name}", user.name)
        if "{user.nick}" in params:
            params = params.replace("{user.nick}", user.nick or user.display_name)
        if "{user.display}" in params:
            params = params.replace("{user.display}", user.display_name)
        if "{user.mention}" in params:
            params = params.replace("{user.mention}", user.mention)
        if "{user.discriminator}" in params:
            params = params.replace("{user.discriminator}", user.discriminator)
        if "{user.avatar}" in params:
            if user.avatar:
                params = params.replace("{user.avatar}", user.avatar.url)
            else:
                params = params.replace("{user.avatar}", user.default_avatar.url)
        if "{user.guild.avatar}" in params:
            if user.guild_avatar:
                params = params.replace("{user.guild.avatar}", user.guild_avatar.url)
            elif user.avatar:
                params = params.replace("{user.guild.avatar}", user.avatar.url)
            else:
                params = params.replace("{user.guild.avatar}", user.default_avatar.url)
        if "{user.joined_at}" in params:
            params = params.replace("{user.joined_at}", discord.utils.format_dt(user.joined_at, style="R"))
        if "{user.created_at}" in params:
            params = params.replace("{user.created_at}", discord.utils.format_dt(user.created_at, style="R"))
        if "{guild.name}" in params:
            params = params.replace("{guild.name}", user.guild.name)
        if "{guild.count}" in params:
            params = params.replace("{guild.count}", str(user.guild.member_count))
        if "{guild.count.format}" in params:
            params = params.replace("{guild.count.format}", self.ordinal(len(user.guild.members)))
        if "{guild.id}" in params:
            params = params.replace("{guild.id}", str(user.guild.id))
        if "{guild.created_at}" in params:
            params = params.replace("{guild.created_at}", discord.utils.format_dt(user.guild.created_at, style="R"))
        if "{guild.boost_count}" in params:
            params = params.replace("{guild.boost_count}", str(user.guild.premium_subscription_count))
        if "{guild.booster_count}" in params:
            params = params.replace("{guild.booster_count}", str(len(user.guild.premium_subscribers)))
        if "{guild.boost_count.format}" in params:
            params = params.replace("{guild.boost_count.format}", self.ordinal(user.guild.premium_subscription_count))
        if "{guild.booster_count.format}" in params:
            params = params.replace("{guild.booster_count.format}", self.ordinal(len(user.guild.premium_subscribers)))
        if "{guild.boost_tier}" in params:
            params = params.replace("{guild.boost_tier}", str(user.guild.premium_tier))
        if "{guild.vanity}" in params:
            params = params.replace("{guild.vanity}", str(user.guild.vanity_url_code) or "none")
        if "{invisible}" in params:
            params = params.replace("{invisible}", "2b2d31")
        if "{botcolor}" in params:
            params = params.replace("{botcolor}", "729bb0")
        if "{botavatar}" in params:
            params = params.replace("{botavatar}", "https://cdn.discordapp.com/icons/1228371886690537624/494604786a585cd444a4a7946381dead.png")
        if "{guild.icon}" in params:
            if user.guild.icon:
                params = params.replace("{guild.icon}", user.guild.icon.url)
            else:
                params = params.replace("{guild.icon}", "https://none.none")
        return params

    def get_parts(self, params: str) -> list:
        if params is None:
            return None
        params = params.replace("{embed}", "")
        return [p[1:][:-1] for p in params.split("$v")]

    def validator(self, text: str, max_len: int, error: str):
        if len(text) >= max_len:
            raise commands.BadArgument(error)

    def is_url(self, text: str):
        regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s!()\[\]{};:'\".,<>?«»“”‘’]))"
        return bool(re.search(regex, text))

    def to_object(self, params: str) -> tuple:
        x = {}
        fields = []
        content = None
        view = discord.ui.View()
        delete_after = None

        for part in self.get_parts(params):
            if part.startswith("content:"):
                content = part[len("content:"):]
                self.validator(content, 2000, "Message content too long")
            if part.startswith("title:"):
                x["title"] = part[len("title:"):]
                self.validator(part[len("title:"):], 256, "Embed title too long")
            if part.startswith("url:"):
                url = part[len("url:"):].strip()
                if self.is_url(url):
                    x["url"] = url
            if part.startswith("description:"):
                x["description"] = part[len("description:"):]
                self.validator(part[len("description:"):], 2048, "Embed description too long")
            if part.startswith("color:"):
                try:
                    x["color"] = int(part[len("color:"):].replace("#", ""), 16)
                except:
                    x["color"] = int("808080", 16)
            if part.startswith("thumbnail:"):
                thumbnail_url = part[len("thumbnail:"):].strip()
                if self.is_url(thumbnail_url):
                    x["thumbnail"] = {"url": thumbnail_url}
            if part.startswith("image:"):
                image_url = part[len("image:"):].strip()
                if self.is_url(image_url):
                    x["image"] = {"url": image_url}
            if part == "timestamp":
                x["timestamp"] = datetime.datetime.now().isoformat()
            if part.startswith("delete:"):
                try:
                    delete_after = float(part[len("delete: "):])
                    if delete_after > 30:
                        delete_after = 30
                except:
                    delete_after = None
            if part.startswith("author:"):
                author_parts = part[len("author: "):].split(" && ")
                name = None
                url = None
                icon_url = None
                for z in author_parts:
                    if z.startswith("name:"):
                        name = z[len("name:"):]
                        self.validator(name, 256, "author name too long")
                    if z.startswith("icon:"):
                        icon_url = z[len("icon:"):]
                        icon_url = icon_url if self.is_url(icon_url) else None
                    if z.startswith("url:"):
                        url = z[len("url:"):]
                        url = url if self.is_url(url) else None
                x["author"] = {"name": name}
                if icon_url:
                    x["author"]["icon_url"] = icon_url
                if url:
                    x["author"]["url"] = url
            if part.startswith("field:"):
                name = None
                value = None
                inline = False
                field_parts = part[len("field: "):].split(" && ")
                for z in field_parts:
                    if z.startswith("name:"):
                        name = z[len("name:"):]
                        self.validator(name, 256, "field name too long")
                    if z.startswith("value:"):
                        value = z[len("value:"):]
                        self.validator(value, 1024, "field value too long")
                    if z.strip() == "inline":
                        inline = True
                fields.append({"name": name, "value": value, "inline": inline})
            if part.startswith("footer:"):
                text = None
                icon_url = None
                footer_parts = part[len("footer: "):].split(" && ")
                for z in footer_parts:
                    if z.startswith("text:"):
                        text = z[len("text:"):]
                        self.validator(text, 2048, "footer text too long")
                    if z.startswith("icon:"):
                        icon_url = z[len("icon:"):]
                        if not self.is_url(icon_url):
                            icon_url = None
                if text:
                    x["footer"] = {"text": text}
                    if icon_url:
                        x["footer"]["icon_url"] = icon_url
            if part.startswith("button:"):
                z = part[len("button:"):].split(" && ")
                disabled = True
                style = discord.ButtonStyle.gray
                emoji = None
                label = None
                url = None
                for m in z:
                    if "label:" in m:
                        label = m.replace("label:", "")
                    if "url:" in m:
                        url = m.replace("url:", "").strip()
                        if self.is_url(url):
                            disabled = False
                    if "emoji:" in m:
                        emoji = m.replace("emoji:", "").strip()
                    if "disabled" in m:
                        disabled = True
                    if "style:" in m:
                        style_name = m.replace("style:", "").strip()
                        style = {
                            "red": discord.ButtonStyle.red,
                            "green": discord.ButtonStyle.green,
                            "gray": discord.ButtonStyle.gray,
                            "blue": discord.ButtonStyle.blurple
                        }.get(style_name, discord.ButtonStyle.gray)
                view.add_item(discord.ui.Button(style=style, label=label, emoji=emoji, url=url, disabled=disabled))

        if not x.get("title") and not x.get("description") and not x.get("image") and not content and not x.get("author"):
            if x:
                try:
                    raise commands.BadArgument("Either **title**, **description**, **author** or **image** is required for the embed.")
                except:
                    return None, None, None, None
        if not x:
            embed = None
        else:
            x["fields"] = fields
            if len(fields) > 25:
                try:
                    raise commands.BadArgument("There are more than **25** fields in your embed")
                except:
                    return None, None, None, None
            embed = discord.Embed.from_dict(x)

        return content, embed, view, delete_after

    def copy_embed(self, message: discord.Message) -> str:
        to_return = ""
        if embeds := message.embeds:
            for embed in embeds:
                embed_dict: dict = discord.Embed.to_dict(embed)
                to_return += "{embed}"
                if embed_dict.get("color"):
                    to_return += "$v{color: " + hex(embed_dict["color"]).replace("0x", "#") + "}"
                if embed_dict.get("title"):
                    to_return += "$v{title: " + embed_dict["title"] + "}"
                if embed_dict.get("url"):
                    to_return += "$v{url: " + embed_dict['url'] + "}"
                if embed_dict.get("description"):
                    to_return += "$v{description: " + embed_dict["description"] + "}"
                if embed_dict.get("author"):
                    author = embed_dict["author"]
                    to_return += "$v{author: "
                    if author.get("name"):
                        to_return += f"name: {author.get('name')}"
                    if author.get("icon_url"):
                        to_return += f" && icon: {author.get('icon_url')}"
                    if author.get("url"):
                        to_return += f" && url: {author.get('url')}"
                    to_return += "}"
                if embed_dict.get("thumbnail"):
                    to_return += "$v{thumbnail: " + embed_dict["thumbnail"]["url"] + "}"
                if embed_dict.get("image"):
                    to_return += "$v{image: " + embed_dict["image"]["url"] + "}"
                if embed_dict.get("fields"):
                    for field in embed_dict["fields"]:
                        to_return += (
                            "$v{field: "
                            + f"name: {field['name']} && value: {field['value']}{' && inline' if field['inline'] else ''}"
                            + "}"
                        )
                if embed_dict.get("footer"):
                    to_return += "$v{footer: "
                    footer = embed_dict["footer"]
                    if footer.get("text"):
                        to_return += f"text: {footer.get('text')}"
                    if footer.get("icon_url"):
                        to_return += f" && icon: {footer.get('icon_url')}"
                    to_return += "}"
                to_return += "\n\n\n\n\n"
                    
        if message.content:
            to_return += "$v{content: " + message.content + "}"

        if message.components:
            for action_row in message.components:
                for component in action_row.children:
                    if isinstance(component, discord.ui.Button):
                        to_return += "$v{button: "
                        if component.label:
                            to_return += f"label: {component.label}"
                        if component.url:
                            to_return += f" && url: {component.url}"
                        if component.emoji:
                            to_return += f" && emoji: {component.emoji}"
                        if component.style == discord.ButtonStyle.red:
                            to_return += " && style: red"
                        elif component.style == discord.ButtonStyle.green:
                            to_return += " && style: green"
                        elif component.style == discord.ButtonStyle.gray:
                            to_return += " && style: gray"
                        elif component.style == discord.ButtonStyle.blurple:
                            to_return += " && style: blue"
                        to_return += "}"
        return to_return

class EmbedScript(commands.Converter):
    
    async def convert(self, ctx: commands.Context, argument: str):
        x = EmbedBuilder().to_object(EmbedBuilder().embed_replacement(ctx.author, argument))
        if x[0] or x[1]:
            if x[3]:
                return {
                    "content": x[0],
                    "embed": x[1],
                    "view": x[2],
                    "delete_after": x[3],
                }
            else:
                return {"content": x[0], "embed": x[1], "view": x[2]}
        return {"content": EmbedBuilder().embed_replacement(ctx.author, argument)}

    async def alt_convert(self, member: discord.Member, argument: str):
        x = EmbedBuilder().to_object(EmbedBuilder().embed_replacement(member, argument))
        if x[0] or x[1]:
            if x[3]:
                return {
                    "content": x[0],
                    "embed": x[1],
                    "view": x[2],
                    "delete_after": x[3],
                }
            else:
                return {"content": x[0], "embed": x[1], "view": x[2]}
        return {"content": EmbedBuilder().embed_replacement(member, argument)}
    
    async def old_convert(self, member, argument: str):
        x = EmbedBuilder().to_object(EmbedBuilder().embed_replacement(member, argument))
        if x[0] or x[1]:
            if x[3]:
                return {
                    "content": x[0],
                    "embed": x[1],
                    "view": x[2],
                    "delete_after": x[3],
                }
            else:
                return {"content": x[0], "embed": x[1], "view": x[2]}
        return {"content": EmbedBuilder().embed_replacement(member, argument)}