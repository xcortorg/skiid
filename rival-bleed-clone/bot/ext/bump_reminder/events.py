from discord.ext.commands import Cog
from discord.ext import tasks
from discord import (
    Client,
    Embed,
    Member,
    TextChannel,
    Message,
)
from datetime import datetime, timedelta
from asyncio import ensure_future, sleep
from tools import ratelimit
from loguru import logger
from lib.classes.database import Record
from lib.classes.builtins import (
    catch,
)  # suppress a pylance error that doesnt exist moment XD


class Events(Cog):
    def __init__(self: "Events", bot: Client):
        self.bot = bot

    async def cog_load(self):
        self.bump_reminder_loop.start()

    async def cog_unload(self):
        self.bump_reminder_loop.stop()

    @tasks.loop(minutes=120)
    async def bump_reminder_loop(self):
        records = await self.bot.db.fetch("""SELECT * FROM bump_reminder""")
        logger.info(f"Dispatching {len(records)} bump reminders")
        for record in records:
            ensure_future(self.schedule_reminder(record))

    async def schedule_reminder(self, record: Record) -> None:
        reminder_time = record.last_bump + timedelta(hours=2)
        now = datetime.now()
        if now > reminder_time and not record.reminded:
            return
        await sleep((reminder_time - now).timestamp())
        self.bot.dispatch("bump_remind", record)

    async def toggle_lock(self, channel: TextChannel, state: bool) -> None:
        if state:
            await channel.set_permissions(
                channel.guild.default_role,
                send_messages=False,
                reason="Bump Reminder Auto Lock",
            )
        else:
            await channel.set_permissions(
                channel.guild.default_role,
                send_messages=True,
                reason="Bump Reminder Auto Lock",
            )
        return

    def default_embed(self, user: Member):
        return f"{user.mention} its time to bump using `/bump`"

    def default_thankyou_embed(self, user: Member):
        return Embed(
            description=f"Thank you {user.mention} for bumping, I will remind you to bump again when its time"
        )

    @Cog.listener("on_bump_remind")
    async def on_bump_remind(self, record: Record):
        if not (guild := self.bot.get_guild(record.guild_id)):
            return
        if not (channel := guild.get_channel(record.channel_id)):
            return
        if not (member := guild.get_member(record.last_bump_user_id)):
            member = self.bot.user
        if not record.message:
            message = await channel.send(content=self.default_embed(member))
        else:
            message = await self.bot.send_embed(channel, record.message, member=member)
        await self.bot.db.execute(
            """UPDATE bump_reminder SET reminded = $1, last_reminder = $2 WHERE guild_id = $3""",
            True,
            message.id,
            record.guild_id,
        )
        if record.auto_lock:
            await self.toggle_lock(channel, False)

    @ratelimit("cleanup:{message.guild.id}", 1, 10, True)
    async def cleanup(self, config: Record, message: Message) -> bool:
        if ty_message := config.last_thankyou_message:
            with catch():
                await self.bot.http.delete_message(message.channel.id, ty_message)
        if last_reminder := config.last_reminder:
            with catch():
                await self.bot.http.delete_message(message.channel.id, last_reminder)
        if config.auto_lock:
            await self.toggle_lock(message.channel, True)
        return True

    @Cog.listener("on_message")
    async def on_message(self, message: Message):
        if not message.guild:
            return
        if not (
            config := await self.bot.db.fetchrow(
                """SELECT * FROM bump_reminder WHERE guild_id = $1""", message.guild.id
            )
        ):
            return
        if (
            message.author.id == 302050872383242240
            and len(message.embeds) == 1
            and "Bump done!" in message.embeds[0].description
        ):
            if not (channel := message.guild.get_channel(config.channel_id)):
                return
            user = message.interaction_metadata.user
            if not config.thankyou_message:
                embed = self.default_thankyou_embed(user)
                message = await channel.send(embed=embed)
            else:
                message = await self.bot.send_embed(
                    channel, config.thankyou_message, user=user
                )
            await self.cleanup(config, message)
            await self.bot.db.execute(
                """
                UPDATE bump_reminder 
                SET last_bump_user_id = $1, last_thankyou_message = $2, last_bump = $3, reminded = $4 
                WHERE guild_id = $5
                """,
                user.id,
                message.id,
                datetime.now(),
                False,
                message.guild.id,
            )
        else:
            if config.auto_clean:
                await message.delete()
