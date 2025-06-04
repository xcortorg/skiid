import asyncio

from discord import RawReactionActionEvent, Reaction, User
from discord.ext.commands import Cog

from modules.evelinabot import Evelina
from events.methods.reaction import ReactionMethods
from modules.misc.utils import safe_method_call

class Reactions(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.reaction_methods = ReactionMethods(bot)

    @Cog.listener("on_raw_reaction_add")
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        if self.bot.is_ready():
            tasks = [
                safe_method_call(self.reaction_methods.on_reactionrole_add, payload),
                safe_method_call(self.reaction_methods.on_starboard_add, payload),
                safe_method_call(self.reaction_methods.on_clownboard_add, payload)
            ]
            await asyncio.gather(*tasks)

    @Cog.listener("on_raw_reaction_remove")
    async def on_raw_reaction_remove(self, payload: RawReactionActionEvent):
        if self.bot.is_ready():
            tasks = [
                safe_method_call(self.reaction_methods.on_reactionrole_remove, payload),
                safe_method_call(self.reaction_methods.on_starboard_remove, payload),
                safe_method_call(self.reaction_methods.on_clownboard_remove, payload)
            ]
            await asyncio.gather(*tasks)

    @Cog.listener("on_reaction_remove")
    async def on_reaction_remove(self, reaction: Reaction, user: User):
        if self.bot.is_ready():
            tasks = [
                safe_method_call(self.reaction_methods.on_reactionsnipe_event, reaction, user)
            ]
            await asyncio.gather(*tasks)

async def setup(bot: Evelina) -> None:
    return await bot.add_cog(Reactions(bot))