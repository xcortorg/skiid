import asyncio
from discord import Message
from discord.ext.commands import Cog

from modules.evelinabot import Evelina
from events.methods.message import MessageMethods
from modules.misc.utils import safe_method_call

class Messages(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.message_methods = MessageMethods(bot)

    @Cog.listener("on_message")
    async def on_message(self, message: Message):
        if self.bot.is_ready():
            tasks = [
                safe_method_call(self.message_methods.on_reposter_message, message),
                safe_method_call(self.message_methods.on_bump_message, message),
                safe_method_call(self.message_methods.on_boost_message, message),
                safe_method_call(self.message_methods.on_autoresponder_event, message),
                safe_method_call(self.message_methods.on_autoreact_event, message),
                safe_method_call(self.message_methods.on_channeltype_check, message),
                safe_method_call(self.message_methods.on_directmessage_event, message),
                safe_method_call(self.message_methods.on_messagestats_event, message),
                safe_method_call(self.message_methods.on_uwulock_message, message),
                safe_method_call(self.message_methods.on_announce_message, message),
                safe_method_call(self.message_methods.on_seen_event, message),
                safe_method_call(self.message_methods.on_stickymessage_event, message),
                safe_method_call(self.message_methods.on_afk_event, message),
                safe_method_call(self.message_methods.on_counting_message, message),
                safe_method_call(self.message_methods.on_antispam_event, message),
                safe_method_call(self.message_methods.on_antirepeat_event, message),
                safe_method_call(self.message_methods.on_lastfm_message, message),
                safe_method_call(self.message_methods.on_leveling_message, message),
                safe_method_call(self.message_methods.on_ping_message, message),
                safe_method_call(self.message_methods.on_last_message, message),
                safe_method_call(self.message_methods.on_gtn_message, message)
            ]
            await asyncio.gather(*tasks)

    @Cog.listener("on_message_delete")
    async def on_message_delete(self, message: Message):
        if self.bot.is_ready():
            tasks = [
                safe_method_call(self.message_methods.on_message_delete_logging, message),
                safe_method_call(self.message_methods.on_snipe_event, message),
                safe_method_call(self.message_methods.on_counting_event, message)
            ]
            await asyncio.gather(*tasks)

    @Cog.listener("on_message_bulk_delete")
    async def on_message_bulk_delete(self, messages):
        if self.bot.is_ready():
            tasks = [
                safe_method_call(self.message_methods.on_bulk_message_delete_logging, messages)
            ]
            await asyncio.gather(*tasks)

    @Cog.listener("on_message_edit")
    async def on_message_edit(self, before: Message, after: Message):
        if self.bot.is_ready():
            tasks = [
                safe_method_call(self.message_methods.on_editsnipe_event, before, after),
                safe_method_call(self.message_methods.on_countingedit_event, before, after),
                safe_method_call(self.message_methods.on_message_edit_logging, before, after),
                safe_method_call(self.message_methods.on_message_edit_link, before, after)
            ]
            await asyncio.gather(*tasks)

async def setup(bot: Evelina) -> None:
    return await bot.add_cog(Messages(bot))