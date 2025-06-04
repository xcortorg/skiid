from discord.ext.commands import Cog
from discord import (
    Client,
    Embed,
    Member,
    RawReactionActionEvent,
    TextChannel,
    Guild,
    utils,
)
from lib.classes.database import Record
from discord.ext import tasks
from datetime import datetime
from random import sample
from loguru import logger
from lib.classes.builtins import get_error
from collections import defaultdict
from asyncio import Lock


class Events(Cog):
    def __init__(self: "Events", bot: Client):
        self.bot = bot
        self.debug = False
        self.locks = defaultdict(Lock)

    async def cog_load(self):
        self.giveaway_check.start()

    async def cog_unload(self):
        self.giveaway_check.stop()

    @tasks.loop(seconds=10)
    async def giveaway_check(self):
        async with self.locks["giveaway"]:
            try:
                for giveaway in await self.bot.db.fetch(
                    """SELECT * FROM giveaways""", cached=False
                ):
                    if giveaway.win_message_id:
                        continue
                    if giveaway.expiration <= utils.utcnow():
                        logger.info(f"giveaway ended")
                        channel = self.bot.get_channel(giveaway.channel_id)
                        if channel:
                            self.bot.dispatch(
                                "giveaway_end", channel.guild, channel, giveaway
                            )
                        else:
                            logger.info(
                                f"{giveaway.expiration.timestamp()} - {utils.utcnow().timestamp()}"
                            )
            except Exception as e:
                logger.error(f"Error in giveaway_check: {get_error(e)}")

    async def check_requirements(self, member: Member, giveaway: Record):
        days_stayed = int((utils.utcnow() - member.joined_at).days)
        account_age = int((utils.utcnow() - member.created_at).days)
        if member.id in giveaway.hosts:
            self.log(f"member {member.id} is a host")
            return False
        member_level = await self.bot.get_cog("Level").get_level(member)
        if giveaway.min_stay > 0:
            if days_stayed < giveaway.min_stay:
                self.log(
                    f"hasnt stayed for the required days of {giveaway.min_stay} - {days_stayed}"
                )
                return False
        if giveaway.max_level > 0:
            if giveaway.max_level < member_level:
                self.log(f"not max level {giveaway.max_level} - {member_level}")
                return False
        if giveaway.min_level > 0:
            if giveaway.min_level > member_level:
                self.log(f"not min level {giveaway.min_level} - {member_level}")
                return False
        if required_roles := giveaway.required_roles:
            member_roles = [r.id for r in member.roles]
            if not set(member_roles) & set(required_roles):
                self.log(
                    f"not required roles {giveaway.required_roles} - {member_roles}"
                )
                return False
        if giveaway.age > 0:
            if account_age < giveaway.age:
                self.log(f"not min age {giveaway.age} - {account_age}")
                return False

        return True

    def log(self, message: str):
        if not self.debug:
            return
        logger.info(message)
        return

    @Cog.listener("on_giveaway_end")
    async def giveaway_ended(
        self, guild: Guild, channel: TextChannel, giveaway: Record
    ):
        message = await channel.fetch_message(giveaway.message_id)
        valid_entries = []
        if len(giveaway.entries) == 0:
            await message.reply("No entries for this giveaway.")

        for entry in giveaway.entries:
            if member := guild.get_member(entry):
                if await self.check_requirements(member, giveaway):
                    valid_entries.append(member)
        if len(valid_entries) < giveaway.winner_count:
            winners = valid_entries
        else:
            winners = sample(valid_entries, giveaway.winner_count)
        logger.info(winners)
        winners_string = ", ".join(m.mention for m in winners)
        hosts_string = ", ".join(f"<@!{u}>" for u in giveaway.hosts)
        embed = Embed(
            title="Giveaway Ended",
            description=f"The giveaway has ended.\n**Winners:** {winners_string}\n**Hosted By:** {hosts_string}",
        )
        win_message = await message.reply(embed=embed)
        await self.bot.db.execute(
            """UPDATE giveaways SET win_message_id = $1 WHERE message_id = $2""",
            win_message.id,
            giveaway.message_id,
        )

    @Cog.listener("on_raw_reaction_add")
    async def on_giveaway_enter(self, payload: RawReactionActionEvent):
        if str(payload.emoji) != "🎉":
            return self.log(f"{str(payload.emoji)} is not the correct emoji")
        if not (guild := self.bot.get_guild(payload.guild_id)):
            return self.log("no guild")
        if not (member := guild.get_member(payload.user_id)):
            return self.log("no member")
        if member.bot:
            return self.log("member is bot")
        if not (
            entries := await self.bot.db.fetchval(
                """SELECT entries FROM giveaways WHERE message_id = $1""",
                payload.message_id,
                cached=False,
            )
        ):
            entries = []
        if member.id in entries:
            return self.log("memebr in entries")
        entries.append(member.id)
        await self.bot.db.execute(
            """UPDATE giveaways SET entries = $1 WHERE message_id = $2""",
            entries,
            payload.message_id,
        )

    @Cog.listener("on_raw_reaction_remove")
    async def on_giveaway_leave(self, payload: RawReactionActionEvent):
        if str(payload.emoji) != "🎉":
            return
        if not (guild := self.bot.get_guild(payload.guild_id)):
            return
        if not (member := guild.get_member(payload.user_id)):
            return
        if member.bot:
            return
        if not (
            entries := await self.bot.db.fetchval(
                """SELECT entries FROM giveaways WHERE message_id = $1""",
                payload.message_id,
            )
        ):
            return
        if member.id not in entries:
            return
        entries.remove(member.id)
        await self.bot.db.execute(
            """UPDATE giveaways SET entries = $1 WHERE message_id = $2""",
            entries,
            payload.message_id,
        )
