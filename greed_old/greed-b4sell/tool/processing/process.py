from typing import Union
from discord import User, Member, Guild
from discord.abc import GuildChannel


def serialize_object(obj):
    if isinstance(obj, (dict, list, tuple, str, int, float)):
        return obj
    if hasattr(obj, "__dict__"):
        return obj.__dict__()
    if hasattr(obj, "__slots__"):
        data = {}
        for s in obj.__slots__:
            data[s] = serialize_object(obj.__getattribute__(s))
        return data


def dump(obj: Union[Member, User, Guild, GuildChannel]) -> dict:
    if isinstance(obj, Guild):
        guild = obj
        return {
            "name": guild.name,
            "afk_channel": guild._afk_channel_id,
            "afk_timeout": guild.afk_timeout,
            "rules_channel": guild._rules_channel_id,
            "community_updates": guild._public_updates_channel_id,
            "system": {
                "channel": guild._system_channel_id,
                "flags": guild._system_channel_flags,
            },
            "categories": [
                {
                    "id": channel.id,
                    "name": channel.name,
                    "position": channel.position,
                    "overwrites": {
                        str(target.id): overwrite._values
                        for target, overwrite in channel.overwrites.items()
                    },
                }
                for channel in guild.categories
            ],
            "text_channels": [
                {
                    "id": channel.id,
                    "name": channel.name,
                    "type": channel.type.value,
                    "position": channel.position,
                    "topic": channel.topic,
                    "slowmode_delay": channel.slowmode_delay,
                    "nsfw": channel.is_nsfw(),
                    "category_id": channel.category_id,
                    "overwrites": {
                        str(target.id): overwrite._values
                        for target, overwrite in channel.overwrites.items()
                    },
                }
                for channel in guild.text_channels
            ],
            "voice_channels": [
                {
                    "id": channel.id,
                    "name": channel.name,
                    "position": channel.position,
                    "category_id": channel.category_id,
                    "overwrites": {
                        str(target.id): overwrite._values
                        for target, overwrite in channel.overwrites.items()
                    },
                }
                for channel in guild.voice_channels
            ],
            "roles": [
                {
                    "id": role.id,
                    "name": role.name,
                    "position": role.position,
                    "color": role.color.value,
                    "hoist": role.hoist,
                    "default": role.is_default(),
                    "premium": role.is_premium_subscriber(),
                    "permissions": role.permissions.value,
                    "members": (
                        [member.id for member in role.members]
                        if not role.is_default()
                        else []
                    ),
                }
                for role in guild.roles
            ],
        }
    else:
        return serialize_object(obj)
