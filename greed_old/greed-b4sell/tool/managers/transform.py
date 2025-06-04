from discord import (
    Member,
    Guild,
    User,
    Client,
    TextChannel,
    VoiceChannel,
    CategoryChannel,
)
from typing import Union, Optional, Dict, Any, List


def asDict(obj, max_depth=5) -> dict:
    """
    Recursively extract all properties from a class and its nested property classes into a dictionary.

    :param obj: The class instance from which to extract properties.
    :param max_depth: The maximum depth to recurse.
    :return: A dictionary containing the properties and their values.
    """

    def is_property(obj):
        return isinstance(obj, property)

    def get_properties(obj, depth, seen):
        if depth > max_depth or id(obj) in seen:
            return {}  # Avoid infinite recursion and limit depth
        seen.add(id(obj))

        properties = {}
        for name, value in obj.__class__.__dict__.items():
            if is_property(value):
                try:
                    prop_value = getattr(obj, name)
                    if hasattr(prop_value, "__class__") and not isinstance(
                        prop_value, (int, float, str, bool, type(None))
                    ):
                        try:
                            properties[name] = get_properties(
                                prop_value, depth + 1, seen
                            )
                        except AttributeError:
                            continue
                    else:
                        properties[name] = prop_value
                except RecursionError:
                    properties[name] = "RecursionError"
        return properties

    return get_properties(obj, 0, set())


class Transformers:
    def __init__(self, bot: Client):
        self.bot = bot

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

    def transform_channel(
        self, channel: Union[TextChannel, VoiceChannel, CategoryChannel, dict]
    ) -> Optional[Union[Dict[Any, Any], TextChannel, VoiceChannel, CategoryChannel]]:
        if isinstance(channel, dict):
            channel_type = channel.get("type")
            if channel_type == 0:
                return TextChannel(state=self._connection, guild=None, data=channel)
            elif channel_type == 2:
                return VoiceChannel(state=self._connection, guild=None, data=channel)
            elif channel_type == 4:
                return CategoryChannel(state=self._connection, guild=None, data=channel)
            else:
                raise ValueError(f"Unsupported channel type: {channel_type}")
        else:
            return asDict(channel)
