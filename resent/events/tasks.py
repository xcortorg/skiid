import asyncio
import datetime
import json
import os
import random

import arrow
import discord
from discord.ext import commands, tasks
from discord.ext.commands import check


@commands.Cog.listener()
async def on_ready(self):
    await self.bot.wait_until_ready()
    counter_update.start(self.bot)
    delete.start(self.bot)
    asyncio.ensure_future(autoposting("pfps"))
    asyncio.ensure_future(autoposting("banners"))


class Tasks(commands.Cog):
    def __init__(self, bot: commands.AutoShardedBot):
        self.bot = bot


@tasks.loop(minutes=10)
async def counter_update(bot: commands.AutoShardedBot):
    results = await bot.db.fetch("SELECT * FROM counters")
    for result in results:
        channel = bot.get_channel(int(result["channel_id"]))
        if channel:
            guild = channel.guild
            module = result["module"]
            if module == "members":
                target = str(guild.member_count)
            elif module == "humans":
                target = str(len([m for m in guild.members if not m.bot]))
            elif module == "bots":
                target = str(len([m for m in guild.members if m.bot]))
            elif module == "boosters":
                target = str(len(guild.premium_subscribers))
            elif module == "voice":
                target = str(sum(len(c.members) for c in guild.voice_channels))
            name = result["channel_name"].replace("{target}", target)
            await channel.edit(name=name, reason="updating counter")


@tasks.loop(hours=6)
async def delete(bot):
    lis = ["snipe", "reactionsnipe", "editsnipe"]
    for l in lis:
        await bot.db.execute(f"DELETE FROM {l}")


@tasks.loop(seconds=5)
async def gw_loop(bot: commands.AutoShardedBot):
    results = await bot.db.fetch("SELECT * FROM giveaway")
    date = datetime.datetime.now()
    for result in results:
        if date.timestamp() > result["finish"].timestamp():
            await gwend_task(bot, result, date)


async def gwend_task(bot: commands.AutoShardedBot, result, date: datetime.datetime):
    members = json.loads(result["members"])
    winners = result["winners"]
    channel_id = result["channel_id"]
    message_id = result["message_id"]
    channel = bot.get_channel(channel_id)
    if channel:
        message = await channel.fetch_message(message_id)
        if message:
            wins = []
            if len(members) <= winners:
                embed = discord.Embed(
                    color=bot.color,
                    title=message.embeds[0].title,
                    description=f"Hosted by: <@!{result['host']}>\n\nNot enough entries to determine the winners!",
                )
                await message.edit(embed=embed, view=None)
            else:
                for _ in range(winners):
                    wins.append(random.choice(members))
                embed = discord.Embed(
                    color=bot.color,
                    title=message.embeds[0].title,
                    description=f"Ended <t:{int(date.timestamp())}:R>\nHosted by: <@!{result['host']}>",
                ).add_field(
                    name="winners",
                    value="\n".join([f"**{bot.get_user(w)}** ({w})" for w in wins]),
                )
                await message.edit(embed=embed, view=None)
                await message.reply(
                    f"**{result['title']}** winners:\n"
                    + "\n".join([f"<@{w}> ({w})" for w in wins])
                )
    await bot.db.execute(
        "INSERT INTO gw_ended VALUES ($1,$2,$3)",
        channel_id,
        message_id,
        json.dumps(members),
    )
    await bot.db.execute(
        "DELETE FROM giveaway WHERE channel_id = $1 AND message_id = $2",
        channel_id,
        message_id,
    )


def is_there_a_reminder():
    async def predicate(ctx: commands.Context):
        check = await ctx.bot.db.fetchrow(
            "SELECT * FROM reminder WHERE guild_id = $1 AND user_id = $2",
            ctx.guild.id,
            ctx.author.id,
        )
        if not check:
            await ctx.send_warning("You don't have a reminder set in this server")
        return check is not None

    return check(predicate)


@tasks.loop(seconds=5)
async def reminder_task(bot: commands.AutoShardedBot):
    results = await bot.db.fetch("SELECT * FROM reminder")
    for result in results:
        if datetime.datetime.now().timestamp() > result["date"].timestamp():
            channel = bot.get_channel(int(result["channel_id"]))
            if channel:
                await channel.send(f"🕰️ <@{result['user_id']}> {result['task']}")
                await bot.db.execute(
                    "DELETE FROM reminder WHERE guild_id = $1 AND user_id = $2 AND channel_id = $3",
                    channel.guild.id,
                    result["user_id"],
                    channel.id,
                )


@tasks.loop(seconds=10)
async def bday_task(bot: commands.AutoShardedBot):
    results = await bot.db.fetch("SELECT * FROM birthday")
    for result in results:
        if (
            arrow.get(result["bday"]).day == arrow.utcnow().day
            and arrow.get(result["bday"]).month == arrow.utcnow().month
        ):
            if result["said"] == "false":
                member = await bot.fetch_user(result["user_id"])
                if member:
                    try:
                        await member.send("🎂 Happy birthday!!")
                        await bot.db.execute(
                            "UPDATE birthday SET said = $1 WHERE user_id = $2",
                            "true",
                            result["user_id"],
                        )
                    except:
                        continue
        else:
            if result["said"] == "true":
                await bot.db.execute(
                    "UPDATE birthday SET said = $1 WHERE user_id = $2",
                    "false",
                    result["user_id"],
                )


async def autoposting(self, genre: str):
    if getattr(self, f"{genre}_send"):
        results = await self.db.fetch("SELECT * FROM autopfp WHERE type = $1", genre)

        while results:
            for result in results:
                if channel := self.get_channel(result.channel_id):
                    await asyncio.sleep(0.001)
                    directory = "./images"
                    category = (
                        result.category
                        if result.category != "random"
                        else random.choice(os.listdir(directory))
                    ).capitalize()
                    if category in os.listdir(directory):
                        try:
                            directory += f"/{category}"
                            file_path = (
                                directory + "/" + random.choice(os.listdir(directory))
                            )
                            file = discord.File(file_path)
                            embed = (
                                discord.Embed(color=self.color)
                                .set_image(url=f"attachment://{file.filename}")
                                .set_footer(text=f"{result.type} module: {category}")
                            )

                            await channel.send(embed=embed, file=file)
                            await asyncio.sleep(4)
                        except Exception as e:
                            await self.get_channel(1234770331131056149).send(
                                f"{genre} posting error - {e}"
                            )

            results = await self.db.fetch(
                "SELECT * FROM autopfp WHERE type = $1", genre
            )
            await asyncio.sleep(7)

        await self.get_channel(1234770331131056149).send(f"Stopped sending {genre}")
        setattr(self, f"{genre}_send", False)


async def setup(bot: commands.AutoShardedBot) -> None:
    await bot.add_cog(Tasks(bot))
