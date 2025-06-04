import asyncio
import datetime
import re
from typing import Any, Optional, Union

import discord
from discord.ext import commands
from munch import Munch
from pydantic import BaseModel


class User(BaseModel):
    mention: str
    id: int
    name: str
    discriminator: str
    created_at: Any
    joined_at: Any
    avatar: str
    global_name: str

    def __str__(self):
        return (
            self.name
            if self.discriminator != "0"
            else f"{self.name}#{self.discriminator}"
        )


class Guild(BaseModel):
    name: str
    icon: Optional[str]
    banner: Optional[str]
    created_at: Any
    owner: User
    member_count: int
    description: Optional[str]
    boost_level: int
    boosts: int

    def __str__(self):
        return self.name


class Script(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str):
        x = await ctx.bot.embed.convert(ctx.author, argument)
        return x


class Embed:
    def init_models(self, member: Union[discord.Member, discord.User]):
        user = User(
            mention=member.mention,
            id=member.id,
            name=member.name,
            discriminator=member.discriminator,
            created_at=member.created_at,
            joined_at=member.joined_at,
            avatar=member.display_avatar.url,
            global_name=member.global_name or member.name,
        )
        kwargs = {"user": user}

        if isinstance(member, discord.Member):
            o = member.guild.owner

            owner = User(
                mention=o.mention,
                id=o.id,
                name=o.name,
                discriminator=o.discriminator,
                created_at=o.created_at,
                joined_at=o.joined_at,
                avatar=o.display_avatar.url,
                global_name=o.global_name or member.name,
            )

            guild = Guild(
                name=member.guild.name,
                id=member.guild.id,
                icon=str(member.guild.icon),
                banner=str(member.guild.banner),
                created_at=member.guild.created_at,
                owner=owner,
                member_count=member.guild.member_count,
                description=member.guild.description,
                boosts=member.guild.premium_subscription_count,
                boost_level=member.guild.premium_tier,
                vanity_code=member.guild.vanity_url_code,
            )
            kwargs["guild"] = guild

        return kwargs

    def get_params(self, text: str) -> Union[tuple, str]:
        results = re.findall(r"\{([^{}]+?):\s*((?:[^{}]|(?:\{[^{}]*?\}))+)\}", text)
        return results or text

    def find(self, l: list, index: int) -> Optional[Any]:
        try:
            return l[index]
        except IndexError:
            return ""

    async def convert(
        self: "Embed",
        member: Union[discord.Member, discord.User],
        text: str,
        new_models: Optional[dict] = None,
    ) -> dict:
        models = self.init_models(member)
        if new_models:
            models.update(new_models)

        content: Optional[str] = None
        embed: Optional[discord.Embed] = None
        delete_after: Optional[int] = None
        view = discord.ui.View()
        dict_embeds = {"fields": []}

        params = self.get_params(text)

        if isinstance(params, str):
            return {"content": params.format(**Munch(**models))}

        for key, value in params:
            await asyncio.sleep(0.1)
            match key:
                case "title":
                    dict_embeds["title"] = value.format(**Munch(**models))
                case "description":
                    dict_embeds["description"] = value.format(**Munch(**models))
                case "thumbnail":
                    dict_embeds["thumbnail"] = {"url": value.format(**Munch(**models))}
                case "image":
                    dict_embeds["image"] = {"url": value.format(**Munch(**models))}
                case "timestamp":
                    match value:
                        case "now":
                            dict_embeds["timestamp"] = (
                                datetime.datetime.now().isoformat()
                            )
                        case "joined_at":
                            dict_embeds["timestamp"] = member.joined_at.timestamp()
                        case "created_at":
                            dict_embeds["timestamp"] = member.created_at.timestamp()
                case "color":
                    try:
                        dict_embeds["color"] = int(value[1:], 16)
                    except ValueError:
                        dict_embeds["color"] = int("2fe136", 16)
                case "content":
                    content = value.format(**Munch(**models))
                case "author":
                    values = value.split(" && ")
                    dict_embeds["author"] = {
                        "name": values[0].format(**Munch(**models)),
                        "icon_url": self.find(values, 1).format(**Munch(**models)),
                        "url": self.find(values, 2).format(**Munch(**models)),
                    }
                case "footer":
                    values = value.split(" && ")
                    dict_embeds["footer"] = {
                        "text": values[0].format(**Munch(**models)),
                        "icon_url": self.find(values, 1).format(**Munch(**models)),
                    }
                case "field":
                    values = value.split(" && ")
                    try:
                        dict_embeds["fields"].append(
                            {
                                "name": values[0].format(**Munch(**models)),
                                "value": values[1].format(**Munch(**models)),
                                "inline": str(self.find(values, 2)).lower() == "true",
                            }
                        )
                    except IndexError:
                        continue
                case "delete":
                    try:
                        delete_after = int(value)
                    except ValueError:
                        continue
                case "button":
                    values = value.split(" && ")
                    try:
                        label = values[0].format(**Munch(**models))
                        url = self.find(values, 1).format(**Munch(**models))
                        view.add_item(
                            discord.ui.Button(
                                label=label,
                                url=url if len(url) > 0 else None,
                                disabled=bool(len(url) == 0),
                            )
                        )
                    except Exception:
                        continue
                case _:
                    continue

            if len(dict_embeds.keys()) > 1:
                embed = discord.Embed.from_dict(dict_embeds)

            return {
                "content": content,
                "embed": embed,
                "view": view,
                "delete_after": delete_after,
            }
