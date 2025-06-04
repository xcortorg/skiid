import asyncio

from discord import User, Member, VoiceState
from discord.ext.commands import Cog

from modules.evelinabot import Evelina
from events.methods.member import MemberMethods
from modules.misc.utils import safe_method_call

class Members(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.member_methods = MemberMethods(bot)

    @Cog.listener("on_user_update")
    async def on_user_update(self, before: User, after: User):
        if self.bot.is_ready():
            tasks = [
                safe_method_call(self.member_methods.on_username_change, before, after),
                safe_method_call(self.member_methods.on_username_tracking, before, after),
                #safe_method_call(self.member_methods.on_avatar_change, before, after)
            ]
            await asyncio.gather(*tasks)

    @Cog.listener("on_member_update")
    async def on_member_update(self, before: Member, after: Member):
        if self.bot.is_ready():
            tasks = [
                safe_method_call(self.member_methods.on_nickname_change, before, after),
                safe_method_call(self.member_methods.on_boost_event, before, after),
                safe_method_call(self.member_methods.on_boost_transfer, before, after),
                safe_method_call(self.member_methods.on_boostaward_event, before, after),
                safe_method_call(self.member_methods.on_forcenickname_event, before, after)
            ]
            await asyncio.gather(*tasks)

    @Cog.listener("on_member_join")
    async def on_member_join(self, member: Member):
        if self.bot.is_ready():
            tasks = [
                safe_method_call(self.member_methods.on_join_event, member),
                safe_method_call(self.member_methods.on_autorole_event, member),
                safe_method_call(self.member_methods.on_whitelist_check, member),
                safe_method_call(self.member_methods.on_invite_join, member),
                safe_method_call(self.member_methods.on_jail_check, member),
                safe_method_call(self.member_methods.on_globalban_check, member),
                safe_method_call(self.member_methods.on_massjoin_event, member),
                safe_method_call(self.member_methods.on_member_join_logging, member),
                safe_method_call(self.member_methods.on_ticket_owner_rejoin, member),
                safe_method_call(self.member_methods.on_activity_join_event, member)
            ]
            await asyncio.gather(*tasks)

    @Cog.listener("on_member_remove")
    async def on_member_remove(self, member: Member):
        if self.bot.is_ready():
            tasks = [
                safe_method_call(self.member_methods.on_leave_event, member),
                safe_method_call(self.member_methods.on_boost_remove, member),
                safe_method_call(self.member_methods.on_invite_leave, member),
                safe_method_call(self.member_methods.on_ticket_leave, member),
                safe_method_call(self.member_methods.on_restore_event, member),
                safe_method_call(self.member_methods.on_member_remove_logging, member),
                safe_method_call(self.member_methods.on_activity_leave_event, member)
            ]
            await asyncio.gather(*tasks)

    @Cog.listener("on_member_unban")
    async def on_member_unban(self, guild, user):
        if self.bot.is_ready():
            tasks = [
                safe_method_call(self.member_methods.on_hardban_check, guild, user)
            ]
            await asyncio.gather(*tasks)

    @Cog.listener("on_voice_state_update")
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
        if self.bot.is_ready():
            tasks = [
                safe_method_call(self.member_methods.on_voicetrack_event, member, before, after),
                safe_method_call(self.member_methods.on_mutetrack_event, member, before, after),
                safe_method_call(self.member_methods.on_voicerole_event, member, before, after),
                safe_method_call(self.member_methods.on_voice_state_update_logging, member, before, after),
                safe_method_call(self.member_methods.on_voiceban_event, member, before, after),
            ]
            await asyncio.gather(*tasks)

async def setup(bot: Evelina) -> None:
    return await bot.add_cog(Members(bot))