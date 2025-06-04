import orjson

from discord.ext.commands import Cog
from discord import (
    Client,
    Message,
    RawReactionActionEvent,
)
from typing import List


class Events(Cog):
    def __init__(self: "Events", bot: Client):
        self.bot = bot

    @Cog.listener("on_raw_reaction_remove")
    async def on_reaction_history(self: "Events", payload: RawReactionActionEvent):
        await self.bot.snipes.add_reaction_history(payload)

    @Cog.listener("on_message_delete")
    async def on_snipe_entry(self: "Events", message: Message):
        if message.author.id == self.bot.user.id:
            return
        return await self.bot.snipes.add_entry("snipe", message)

    @Cog.listener("on_message_edit")
    async def on_edit_snipe(self: "Events", before: Message, after: Message):
        if before.content != after.content and before.author.id != self.bot.user.id:
            return await self.bot.snipes.add_entry("editsnipe", before)

    @Cog.listener("on_raw_reaction_remove")
    async def on_reaction_snipe(self: "Events", payload: RawReactionActionEvent):
        guild = self.bot.get_guild(payload.guild_id)
        channel = guild.get_channel(payload.channel_id)
        if not payload.member:
            payload.member = guild.get_member(
                payload.user_id
            ) or await self.bot.fetch_user(payload.user_id)
        message = await self.bot.fetch_message(channel, payload.message_id)
        return await self.bot.snipes.add_entry(
            "rs", (message, payload.emoji, payload.member)
        )
