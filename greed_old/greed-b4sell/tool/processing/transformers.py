from typing import Optional, Union, Dict, Any, List
from discord import Embed, User, Guild, Member
from discord.ext.commands import AutoShardedBot
from typing_extensions import Self


def asDict(obj: Any) -> Dict[str, Any]:
    return obj.__dict__


TransformedEmbed = Union[Dict[str, str], List[Any], str]


class Transformers:
    """This class is for transforming discord.py objects into dictionaries that are supplyable through an IPC where they have to be json serialized whilst keeping the ability to transform them back into said objects"""

    def __init__(self: Self, bot: AutoShardedBot) -> None:
        self.bot = bot

    def transform_embed(
        self, embed: Embed, to_type: type
    ) -> Optional[TransformedEmbed]:
        content = {
            "title": embed.title,
            "description": embed.description,
            "fields": [
                {"name": field.name, "value": field.value, "inline": field.inline}
                for field in embed.fields
            ],
            "footer": embed.footer.text if embed.footer else None,
            "image_url": embed.image.url if embed.image else None,
            "thumbnail_url": embed.thumbnail.url if embed.thumbnail else None,
            "author": (
                {
                    "name": embed.author.name,
                    "url": embed.author.url,
                    "icon_url": embed.author.icon_url,
                }
                if embed.author
                else None
            ),
            "color": embed.color.value if embed.color else None,
        }

        if to_type is str:
            d = ""
            for key, value in content.items():
                if isinstance(value, str):
                    d += f"{value} "
                elif isinstance(value, list):
                    for v in value:
                        for _ in v.values():
                            d += f"{_} "
            return d
        elif to_type is list:
            return list(content.values())
        elif to_type is dict:
            return content
        else:
            try:
                return to_type(content.values())
            except Exception:
                pass
            raise ValueError(f"Unsupported type: {to_type}")

    def transform_user(
        self, user: Union[User, dict], store: Optional[bool] = False
    ) -> Optional[Union[User, Dict[Any, Any]]]:
        if isinstance(user, dict):
            _ = User(state=self._connection, data=user)
            if store:
                self._connection.store_user(user)
            return _
        else:
            data = asDict(user)
            data["username"] = data["name"]
            return User(state=self._connection, data=data)

    def transform_guild(
        self, guild: Union[Guild, dict], store: Optional[bool] = False
    ) -> Optional[Union[Guild, Dict[Any, Any]]]:
        if isinstance(guild, dict):
            g = self.get_guild(guild.get("id"))
            if not g:
                _ = Guild(state=self._connection, data=guild)
                if store:
                    self._connection.store_guild(guild)
                return _
            else:
                return g
        else:
            data = asDict(guild)
            data["id"] = guild.id
            return data

    def transform_member(
        self,
        member: Union[Member, dict],
        guild: Optional[Union[Dict[Any, Any], Guild]] = None,
        store: Optional[bool] = False,
    ) -> Optional[Union[Member, Dict[Any, Any]]]:
        if isinstance(member, dict):
            if guild:
                guild = self.transform_guild(guild)
                _ = Member(state=self._connection, data=member, guild=guild)
                if store:
                    self._connection.store_member(member)
                return _
            else:
                raise TypeError("Guild was not supplied")
        else:
            data = asDict(member)
            data["guild"] = self.transform_guild(member.guild)
            return data
