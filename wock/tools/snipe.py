import asyncio
import datetime
import typing
from collections import deque

import discord


class SnipeError(discord.ext.commands.errors.CommandError):
    def __init__(self, message, **kwargs):
        super().__init__(message)
        self.kwargs = kwargs


class Snipe(object):
    def __init__(self, bot):
        self.bot = bot
        self.data = {}

    async def add_entry(self, type: str, message: typing.Union[discord.Message, tuple]):
        if isinstance(message, discord.Message):
            entry: dict = {
                "timestamp": message.created_at.timestamp(),
                "content": message.content,
                "embeds": [
                    embed.to_dict()
                    for embed in message.embeds[:8]
                    if not embed.type == "image" and not embed.type == "video"
                ],
                "attachments": [
                    attachment.proxy_url
                    for attachment in (
                        message.attachments
                        + list(
                            (embed.thumbnail or embed.image)
                            for embed in message.embeds
                            if embed.type == "image"
                        )
                    )
                ],
                "stickers": [sticker.url for sticker in message.stickers],
                "author": {
                    "id": message.author.id,
                    "name": message.author.name,
                    "avatar": message.author.display_avatar.url,
                },
            }
        else:
            entry: dict = {
                "timestamp": datetime.datetime.now().timestamp(),
                "message": message[0].message.jump_url,
                "reaction": (
                    str(message[0].emoji)
                    if message[0].is_custom_emoji()
                    else str(message[0].emoji)
                ),
                "author": {
                    "id": message[1].id,
                    "name": message[1].name,
                    "avatar": message[1].display_avatar.url,
                },
            }
        if type.lower() == "snipe":
            if f"s-{message.channel.id}" not in self.data.keys():
                self.data[f"s-{message.channel.id}"] = deque(maxlen=100)
            else:
                if len(self.data[f"s-{message.channel.id}"]) == 100:
                    self.data[f"s-{message.channel.id}"].pop()
            self.data[f"s-{message.channel.id}"].insert(0, entry)
        elif type.lower() == "editsnipe":
            if f"es-{message.channel.id}" not in self.data.keys():
                self.data[f"es-{message.channel.id}"] = deque(maxlen=100)
            else:
                if len(self.data[f"es-{message.channel.id}"]) == 100:
                    self.data[f"es-{message.channel.id}"].pop()
            self.data[f"es-{message.channel.id}"].insert(0, entry)
        else:
            if f"rs-{message[0].message.channel.id}" not in self.data.keys():
                self.data[f"rs-{message[0].message.channel.id}"] = deque(maxlen=100)
            else:
                if len(self.data[f"rs-{message[0].message.channel.id}"]) == 100:
                    self.data[f"rs-{message[0].message.channel.id}"].pop()
            self.data[f"rs-{message[0].message.channel.id}"].insert(0, entry)

        return entry

    async def get_entry(self, channel: discord.TextChannel, type: str, index: int):
        if type.lower() == "snipe":
            if data := self.data.get(f"s-{channel.id}"):
                if len(data) < index - 1:
                    raise SnipeError(
                        f"There are **not** `{index}` **deleted messages**"
                    )
                try:
                    return (data[index - 1], len(data))
                except Exception:
                    raise SnipeError(
                        f"There are **not** `{index}` **deleted messages**"
                    )

            else:
                raise SnipeError(
                    f"There are **no deleted messages** in {channel.mention}"
                )
        elif type.lower() == "editsnipe":
            if data := self.data.get(f"es-{channel.id}"):
                if len(data) < index - 1:
                    raise SnipeError(
                        f"There are **not** `{index}` **edits made** recently"
                    )
                try:
                    return (data[index - 1], len(data))
                except Exception:
                    raise SnipeError(
                        f"There are **not** `{index}` **deleted messages**"
                    )
            else:
                raise SnipeError(
                    f"There are **no messages edited** in {channel.mention}"
                )
        else:
            if data := self.data.get(f"rs-{channel.id}"):
                if len(data) < index - 1:
                    raise SnipeError(
                        f"There has **not** been `{index}` **reactions removed** recently"
                    )
                try:
                    return (data[index - 1], len(data))
                except Exception:
                    raise SnipeError(
                        f"There has **not** been `{index}` **reactions removed**"
                    )
            else:
                raise SnipeError(
                    f"There are **no reaction removals** for **{channel.mention}**"
                )

    async def delete_entry(self, channel: discord.TextChannel, type: str, index: int):
        if type.lower() == "snipe":
            if data := self.data.get(f"s-{channel.id}"):
                self.data[f"s-{channel.id}"].remove(data[index - 1])
            else:
                raise SnipeError(f"There are **not** `{index}` **deleted messages**")
        elif type.lower() == "editsnipe":
            if data := self.data.get(f"es-{channel.id}"):
                self.data[f"es-{channel.id}"].remove(data[index - 1])
            else:
                raise SnipeError(f"There are **not** `{index}` **edits made** recently")
        else:
            if data := self.data.get(f"rs-{channel.id}"):
                self.data[f"rs-{channel.id}"].remove(data[index - 1])
            else:
                raise SnipeError(
                    f"There has **not** been `{index}` **reactions removed** recently"
                )

    async def clear_entries(self, channel: discord.TextChannel):
        async def pop_entry(f: str, channel: discord.TextChannel):
            try:
                self.data.pop(f"{f}{channel.id}")
            except Exception:
                pass

        await asyncio.gather(*[pop_entry(f, channel) for f in ["s-", "es-", "rs-"]])
        return True
