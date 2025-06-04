import asyncio

from discord import Guild, AuditLogEntry, Thread
from discord.abc import GuildChannel
from discord.ext.commands import Cog

from modules.evelinabot import Evelina
from events.methods.guild import GuildMethods
from modules.misc.utils import safe_method_call

class Guilds(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.guild_methods = GuildMethods(bot)

    @Cog.listener("on_guild_update")
    async def on_guild_update(self, before: Guild, after: Guild):
        if self.bot.is_ready():
            tasks = [
                safe_method_call(self.guild_methods.on_guildname_change, before, after),
                safe_method_call(self.guild_methods.on_vanity_change, before, after),
                safe_method_call(self.guild_methods.on_vanity_tracking, before, after)
            ]
            await asyncio.gather(*tasks)

    @Cog.listener("on_guild_role_delete")
    async def on_guild_role_delete(self, role):
        if self.bot.is_ready():
            tasks = [
                safe_method_call(self.guild_methods.on_eventrole_delete, role)
            ]
            await asyncio.gather(*tasks)

    @Cog.listener("on_guild_channel_create")
    async def on_guild_channel_create(self, channel: GuildChannel):
        if self.bot.is_ready():
            tasks = [
                safe_method_call(self.guild_methods.on_moderation_event, channel)
            ]
            await asyncio.gather(*tasks)

    @Cog.listener("on_guild_channel_delete")
    async def on_guild_channel_delete(self, channel: GuildChannel):
        if self.bot.is_ready():
            tasks = [
                safe_method_call(self.guild_methods.on_ticketchannel_delete, channel),
                safe_method_call(self.guild_methods.on_spamchannel_delete, channel),
                safe_method_call(self.guild_methods.on_repeatchannel_delete, channel),
                safe_method_call(self.guild_methods.on_eventchannel_delete, channel)
            ]
            await asyncio.gather(*tasks)

    @Cog.listener("on_thread_update")
    async def on_thread_update(self, before: Thread, after: Thread):
        if self.bot.is_ready():
            tasks = [
                safe_method_call(self.guild_methods.on_thread_update, before, after)
            ]
            await asyncio.gather(*tasks)

    @Cog.listener()
    async def on_audit_log_entry_create(self, entry: AuditLogEntry):
        if self.bot.is_ready():
            tasks = [
                safe_method_call(self.guild_methods.on_audit_log_entry_create_logging, entry)
            ]
            await asyncio.gather(*tasks)

    @Cog.listener()
    async def on_guild_action(self, guild: Guild):
        if self.bot.is_ready():
            tasks = [
                safe_method_call(self.guild_methods.on_invite_create, guild),
                safe_method_call(self.guild_methods.on_invite_delete, guild),
                safe_method_call(self.guild_methods.on_guild_join, guild)
            ]
            await asyncio.gather(*tasks)

async def setup(bot: Evelina) -> None:
    return await bot.add_cog(Guilds(bot))