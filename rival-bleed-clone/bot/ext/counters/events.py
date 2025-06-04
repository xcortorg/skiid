from discord.ext.commands import (
    Cog,
    Context,
    command,
    group,
    CommandError,
    has_permissions,
)
from discord.ext import tasks
import asyncio
from discord import Client, Embed, File, Member, ExpiringDictionary, User, Guild


class Events(Cog):
    def __init__(self: "Events", bot: Client):
        self.bot = bot
        self.rl_helper = ExpiringDictionary()

    @Cog.listener("on_member_join")
    async def on_member_counter_add(self, member: Member):
        guild = member.guild
        if not (
            counter := await self.bot.db.fetchrow(
                """SELECT * FROM counters WHERE guild_id = $1 AND counter_type = $2""",
                guild.id,
                "members",
            )
        ):
            return
        counter_channel = guild.get_channel(counter.channel_id)
        if counter_channel:
            if await self.rl_helper.ratelimit(f"counter_edit:{guild.id}", 1, 10):
                await asyncio.sleep(10)
            await counter_channel.edit(name=f"{len(guild.members)} members")

    @Cog.listener("on_member_remove")
    async def on_member_counter_remove(self, member: Member):
        guild = member.guild
        if not (
            counter := await self.bot.db.fetchrow(
                """SELECT * FROM counters WHERE guild_id = $1 AND counter_type = $2""",
                guild.id,
                "members",
            )
        ):
            return
        counter_channel = guild.get_channel(counter.channel_id)
        if counter_channel:
            if await self.rl_helper.ratelimit(f"counter_edit:{guild.id}", 1, 10):
                await asyncio.sleep(10)
            await counter_channel.edit(name=f"{len(guild.members)} members")

    @Cog.listener("on_member_update")
    async def on_booster_counter_change(self, before: Member, after: Member):
        guild = after.guild
        if not (
            booster_counter := await self.bot.db.fetchrow(
                """SELECT * FROM counters WHERE guild_id = $1 AND counter_type = $2""",
                guild.id,
                "boosters",
            )
        ):
            booster_counter = None
        if not (
            boost_counter := await self.bot.db.fetchrow(
                """SELECT * FROM counters WHERE guild_id = $1 AND counter_type = $2""",
                guild.id,
                "boosts",
            )
        ):
            boost_counter = None
        if not boost_counter and not booster_counter:
            return
        boost_counter_channel = guild.get_channel(boost_counter.channel_id)
        booster_counter_channel = guild.get_channel(booster_counter.channel_id)
        if await self.rl_helper.ratelimit(f"counter_edit:{guild.id}", 1, 10):
            await asyncio.sleep(10)
        if boost_counter_channel:
            num = guild.premium_subscription_count
            await boost_counter_channel.edit(name=f"{num} boosts")
        if booster_counter_channel:
            num = len(guild.premium_subscribers)
            await booster_counter_channel.edit(name=f"{num} boosters")
