import asyncio
import datetime
import json
import re
from collections import defaultdict

import discord
from discord import Embed, File, Message, User
from discord.ext import commands
from headers import Session
from patches.classes import Cache, Messages, Perms
from utils.embed import Embed
from uwuipy import uwuipy

DISCORD_API_LINK = "https://discord.com/api/invite/"


def duration(n: int) -> str:
    uptime = int(n / 1000)
    seconds_to_minute = 60
    seconds_to_hour = 60 * seconds_to_minute
    seconds_to_day = 24 * seconds_to_hour

    days = uptime // seconds_to_day
    uptime %= seconds_to_day

    hours = uptime // seconds_to_hour
    uptime %= seconds_to_hour

    minutes = uptime // seconds_to_minute
    uptime %= seconds_to_minute

    seconds = uptime
    if days > 0:
        return "{} days, {} hours, {} minutes, {} seconds".format(
            days, hours, minutes, seconds
        )
    if hours > 0 and days == 0:
        return "{} hours, {} minutes, {} seconds".format(hours, minutes, seconds)
    if minutes > 0 and hours == 0 and days == 0:
        return "{} minutes, {} seconds".format(minutes, seconds)
    if minutes < 0 and hours == 0 and days == 0:
        return "{} seconds".format(seconds)


async def decrypt_message(content: str) -> str:
    return (
        content.lower()
        .replace("1", "i")
        .replace("4", "a")
        .replace("3", "e")
        .replace("0", "o")
        .replace("@", "a")
    )


class Messages(commands.Cog):
    def __init__(self, bot: commands.AutoShardedBot):
        self.bot = bot
        self.snipes = {}
        self.edit_snipes = {}
        self.session = Session()
        self.locks = defaultdict(asyncio.Lock)
        self.antispam_cache = {}
        self.cache = Cache()

    async def repost_tiktok(self, message: Message):

        async with self.locks[message.guild.id]:

            social = await self.bot.db.fetchrow(
                "SELECT * FROM settings_social WHERE guild_id = $1", message.guild.id
            )

            if not social or not social["toggled"]:
                return

            url = message.content[len("resent") + 1 :]
            try:
                await message.delete()
            except:
                pass

            async with message.channel.typing():
                x = await self.session.get_json(
                    "https://tikwm.com/api/", params={"url": url}
                )
                if x["data"].get("images"):
                    embeds = []
                    for img in x["data"]["images"]:
                        embed = (
                            Embed(
                                color=self.bot.color,
                                description=f"[**Tiktok**]({url}) requested by {message.author}",
                            )
                            .set_author(
                                name=f"@{x['data']['author']['unique_id']}",
                                icon_url=x["data"]["author"]["avatar"],
                                url=url,
                            )
                            .set_footer(
                                text=f"❤️ {x['data']['digg_count']:,}  💬 {x['data']['comment_count']:,} | {x['data']['images'].index(img)+1}/{len(x['data']['images'])}"
                            )
                            .set_image(url=img)
                        )

                    embeds.append(embed)
                    ctx = await self.bot.get_context(message)
                    return await ctx.paginator(embeds)
                else:
                    video = x["data"]["play"]
                    file = File(
                        fp=await self.bot.getbyte(video),
                        filename="resenttiktok.mp4",
                    )
                    embed = Embed(
                        color=self.bot.color,
                        description=(
                            f"[{x['data']['title']}]({url})"
                            if x["data"]["title"]
                            else ""
                        ),
                    ).set_author(
                        name=f"@{x['data']['author']['unique_id']}",
                        icon_url=x["data"]["author"]["avatar"],
                    )
                    x = x["data"]

                    embed.set_footer(
                        text=f"❤️ {x['digg_count']:,}  💬 {x['comment_count']:,}  🔗 {x['share_count']:,}  👀 {x['play_count']:,} | {message.author}"
                    )
                    await message.channel.send(embed=embed, file=file)

    @commands.Cog.listener("on_message")
    async def boost_listener(self, message: discord.Message):
        if "MessageType.premium_guild" in str(message.type):
            if message.guild.id == 952161067033849919:
                member = message.author
                check = await self.bot.db.fetchrow(
                    "SELECT * FROM donor WHERE user_id = $1", member.id
                )
                if check:
                    return
                ts = int(datetime.datetime.now().timestamp())
                await self.bot.db.execute(
                    "INSERT INTO donor VALUES ($1,$2)", member.id, ts
                )
                return await message.channel.send(
                    f"{member.mention}, enjoy your perks! <a:catclap:1081008257776226354>"
                )

    @commands.Cog.listener("on_message")
    async def seen_listener(self, message: discord.Message):
        if not message.guild:
            return
        if message.author.bot:
            return
        check = await self.bot.db.fetchrow(
            "SELECT * FROM seen WHERE guild_id = {} AND user_id = {}".format(
                message.guild.id, message.author.id
            )
        )
        if check is None:
            return await self.bot.db.execute(
                "INSERT INTO seen VALUES ($1,$2,$3)",
                message.guild.id,
                message.author.id,
                int(datetime.datetime.now().timestamp()),
            )
        ts = int(datetime.datetime.now().timestamp())
        await self.bot.db.execute(
            "UPDATE seen SET time = $1 WHERE guild_id = $2 AND user_id = $3",
            ts,
            message.guild.id,
            message.author.id,
        )

    @commands.Cog.listener("on_message")
    async def bump_event(self, message: discord.Message):
        if message.type == discord.MessageType.chat_input_command:
            if (
                message.interaction.name == "bump"
                and message.author.id == 302050872383242240
            ):
                if (
                    "Bump done!" in message.embeds[0].description
                    or "Bump done!" in message.content
                ):
                    check = await self.bot.db.fetchrow(
                        "SELECT * FROM bumps WHERE guild_id = {}".format(
                            message.guild.id
                        )
                    )
                    if check is not None:
                        await message.channel.send(
                            f"{message.interaction.user.mention} thanks for bumping the server. You will be reminded in 2 hours!"
                        )
                        await asyncio.sleep(7200)
                        embed = discord.Embed(
                            color=self.bot.color,
                            description="Bump the server using the `/bump` command",
                        )
                        await message.channel.send(
                            f"{message.interaction.user.mention} time to bump !!",
                            embed=embed,
                        )

    @commands.Cog.listener("on_message")
    async def afk_listener(self, message: discord.Message):
        if not message.guild:
            return
        if message.author.bot:
            return
        if message.mentions:
            if len(message.mentions) == 1:
                mem = message.mentions[0]
                check = await self.bot.db.fetchrow(
                    "SELECT * from afk where guild_id = $1 AND user_id = $2",
                    message.guild.id,
                    mem.id,
                )
                if check:
                    em = discord.Embed(
                        color=self.bot.color,
                        description=f"💤 **{mem}** is AFK since **{self.bot.ext.relative_time(datetime.datetime.fromtimestamp(int(check['time'])))}** - {check['reason']}",
                    )
                    await message.reply(embed=em)
            else:
                embeds = []
                for mem in message.mentions:
                    check = await self.bot.db.fetchrow(
                        "SELECT * from afk where guild_id = $1 AND user_id = $2",
                        message.guild.id,
                        mem.id,
                    )
                    if check:
                        em = discord.Embed(
                            color=self.bot.color,
                            description=f"💤 **{mem}** is AFK since **{self.bot.ext.relative_time(datetime.datetime.fromtimestamp(int(check['time'])))}** - {check['reason']}",
                        )
                        embeds.append(em)
                    if len(embeds) == 10:
                        await message.reply(embeds=embeds)
                        embeds = []
                if len(embeds) > 0:
                    await message.reply(embeds=embeds)
                embeds = []

        che = await self.bot.db.fetchrow(
            "SELECT * from afk where guild_id = $1 AND user_id = $2",
            message.guild.id,
            message.author.id,
        )
        if che:
            embed = discord.Embed(
                color=self.bot.color,
                description=f"<a:wave:1020721034934104074> Welcome back **{message.author}**! You were AFK since **{self.bot.ext.relative_time(datetime.datetime.fromtimestamp(int(che['time'])))}**",
            )
            try:
                await message.reply(embed=embed)
            except:
                pass
            await self.bot.db.execute(
                "DELETE FROM afk WHERE guild_id = $1 AND user_id = $2",
                message.guild.id,
                message.author.id,
            )

    @commands.Cog.listener("on_message_edit")
    async def edit_snipe(self, before: discord.Message, after: discord.Message):
        if not before.guild:
            return
        if before.author.bot:
            return
        await self.bot.db.execute(
            "INSERT INTO editsnipe VALUES ($1,$2,$3,$4,$5,$6)",
            before.guild.id,
            before.channel.id,
            before.author.name,
            before.author.display_avatar.url,
            before.content,
            after.content,
        )

    @commands.Cog.listener("on_message_delete")
    async def snipe(self, message: discord.Message):
        if not message.guild:
            return
        if message.author.bot:
            return
        invites = ["discord.gg/", ".gg/", "discord.com/invite/"]
        if any(invite in message.content for invite in invites):
            check = await self.bot.db.fetchrow(
                "SELECT * FROM antiinvite WHERE guild_id = $1", message.guild.id
            )
            if check:
                return

        attachment = message.attachments[0].url if message.attachments else "none"
        author = str(message.author)
        content = message.content
        avatar = message.author.display_avatar.url
        await self.bot.db.execute(
            "INSERT INTO snipe VALUES ($1,$2,$3,$4,$5,$6,$7)",
            message.guild.id,
            message.channel.id,
            author,
            content,
            attachment,
            avatar,
            datetime.datetime.now(),
        )

    @commands.Cog.listener("on_message")
    async def uwulock(self, message: discord.Message):
        if not message.guild:
            return
        check = await self.bot.db.fetchrow(
            "SELECT user_id FROM uwulock WHERE user_id = $1 AND guild_id = $2",
            message.author.id,
            message.guild.id,
        )
        check1 = check = await self.bot.db.fetchrow(
            "SELECT user_id FROM guwulock WHERE user_id = $1", message.author.id
        )
        if check1:
            return
        if check is None or not check:
            return
        uwu = uwuipy()
        uwu_message = uwu.uwuify(message.content)
        hook = await self.webhook(message.channel)
        await hook.send(
            content=uwu_message,
            username=message.author.display_name,
            avatar_url=message.author.display_avatar,
            thread=(
                message.channel
                if isinstance(message.channel, discord.Thread)
                else discord.utils.MISSING
            ),
        )
        await message.delete()

    @commands.Cog.listener("on_message")
    async def guwulock(self, message: discord.Message):
        if not message.guild:
            return
        check = await self.bot.db.fetchrow(
            "SELECT user_id FROM guwulock WHERE user_id = $1", message.author.id
        )
        check1 = await self.bot.db.fetchrow(
            "SELECT user_id FROM uwulock WHERE user_id = $1 AND guild_id = $2",
            message.author.id,
            message.guild.id,
        )
        if check1:
            return
        if check is None or not check:
            return
        uwu = uwuipy()
        uwu_message = uwu.uwuify(message.content)
        hook = await self.webhook(message.channel)
        await hook.send(
            content=uwu_message,
            username=message.author.display_name,
            avatar_url=message.author.display_avatar,
            thread=(
                message.channel
                if isinstance(message.channel, discord.Thread)
                else discord.utils.MISSING
            ),
        )
        await message.delete()

    async def webhook(self, channel) -> discord.Webhook:
        for webhook in await channel.webhooks():
            if webhook.user == self.bot.user:
                return webhook
        await channel.create_webhook(name="resent")

    @commands.Cog.listener("on_message")
    async def on_message_shutup(self, message: discord.Message):
        if not message.guild:
            return
        check = await self.bot.db.fetchrow(
            "SELECT user_id FROM shutup WHERE user_id = $1 AND guild_id = $2",
            message.author.id,
            message.guild.id,
        )
        if check is None or not check:
            return
        await message.delete()

    @commands.Cog.listener("on_message")
    async def reposter(self, message: Message):
        if (
            message.guild
            and not message.author.bot
            and message.content.startswith("resent")
        ):
            if re.search(
                r"\bhttps?:\/\/(?:m|www|vm)\.tiktok\.com\/\S*?\b(?:(?:(?:usr|v|embed|user|video)\/|\?shareId=|\&item_id=)(\d+)|(?=\w{7})(\w*?[A-Z\d]\w*)(?=\s|\/$))\b",
                message.content[len("resent") + 1 :],
            ):
                return await self.repost_tiktok(message)

    @commands.Cog.listener("on_message")
    async def antispam_send(self, message: discord.Message):
        if not message.guild:
            return
        if isinstance(message.author, discord.User):
            return
        if await Perms.has_perms(await self.bot.get_context(message), "manage_guild"):
            return
        check = await self.bot.db.fetchrow(
            "SELECT * FROM antispam WHERE guild_id = $1", message.guild.id
        )
        if check:
            res1 = await self.bot.db.fetchrow(
                "SELECT * FROM whitelist WHERE guild_id = $1 AND module = $2 AND object_id = $3 AND mode = $4",
                message.guild.id,
                "antispam",
                message.channel.id,
                "channel",
            )
            if not res1:
                res2 = await self.bot.db.fetchrow(
                    "SELECT * FROM whitelist WHERE guild_id = $1 AND module = $2 AND object_id = $3 AND mode = $4",
                    message.guild.id,
                    "antispam",
                    message.author.id,
                    "user",
                )
                if not res2:
                    if not self.antispam_cache.get(str(message.channel.id)):
                        self.antispam_cache[str(message.channel.id)] = {}
                    if not self.antispam_cache[str(message.channel.id)].get(
                        str(message.author.id)
                    ):
                        self.antispam_cache[str(message.channel.id)][
                            str(message.author.id)
                        ] = []
                    self.antispam_cache[str(message.channel.id)][
                        str(message.author.id)
                    ].append(tuple([datetime.datetime.now(), message]))
                    expired_time = check["seconds"]
                    expired_msgs = [
                        msg
                        for msg in self.antispam_cache[str(message.channel.id)][
                            str(message.author.id)
                        ]
                        if (datetime.datetime.now() - msg[0]).total_seconds()
                        > expired_time
                    ]
                    for ex in expired_msgs:
                        self.antispam_cache[str(message.channel.id)][
                            str(message.author.id)
                        ].remove(ex)
                    if (
                        len(
                            self.antispam_cache[str(message.channel.id)][
                                str(message.author.id)
                            ]
                        )
                        > check["count"]
                    ):
                        messages = [
                            msg[1]
                            for msg in self.antispam_cache[str(message.channel.id)][
                                str(message.author.id)
                            ]
                        ]
                        self.antispam_cache[str(message.channel.id)][
                            str(message.author.id)
                        ] = []
                        punishment = check["punishment"]
                        if punishment == "delete":
                            return await message.channel.delete_messages(
                                messages, reason="AutoMod: spamming messages"
                            )
                        await message.channel.delete_messages(
                            messages, reason="AutoMod: spamming messages"
                        )
                        if not message.author.is_timed_out():
                            await message.channel.send(
                                embed=discord.Embed(
                                    color=self.bot.color,
                                    title="AutoMod",
                                    description=f"{self.bot.warning} {message.author.mention}: You have been muted for **1 minute** for spamming messages in this channel",
                                )
                            )
                            await message.author.timeout(
                                discord.utils.utcnow() + datetime.timedelta(minutes=1),
                                reason="AutoMod: spamming messages",
                            )

    @commands.Cog.listener("on_message")
    async def chatfilter_send(self, message: discord.Message):
        if not message.guild:
            return
        if isinstance(message.author, discord.User):
            return
        if await Perms.has_perms(await self.bot.get_context(message), "manage_guild"):
            return
        check = await self.bot.db.fetch(
            "SELECT * FROM chatfilter WHERE guild_id = $1", message.guild.id
        )
        if len(check) > 0:
            res1 = await self.bot.db.fetchrow(
                "SELECT * FROM whitelist WHERE guild_id = $1 AND module = $2 AND object_id = $3 AND mode = $4",
                message.guild.id,
                "chatfilter",
                message.channel.id,
                "channel",
            )
            if not res1:
                res2 = await self.bot.db.fetchrow(
                    "SELECT * FROM whitelist WHERE guild_id = $1 AND module = $2 AND object_id = $3 AND mode = $4",
                    message.guild.id,
                    "chatfilter",
                    message.author.id,
                    "user",
                )
                if not res2:
                    for result in check:
                        if result["word"] in await decrypt_message(message.content):
                            return await message.delete()

    @commands.Cog.listener("on_message_edit")
    async def chatfilter_edit(self, before, after: discord.Message):
        if before.content == after.content:
            return
        message = after
        if not message.guild:
            return
        if isinstance(message.author, discord.User):
            return
        if await Perms.has_perms(await self.bot.get_context(message), "manage_guild"):
            return
        check = await self.bot.db.fetch(
            "SELECT * FROM chatfilter WHERE guild_id = $1", message.guild.id
        )
        if len(check) > 0:
            res1 = await self.bot.db.fetchrow(
                "SELECT * FROM whitelist WHERE guild_id = $1 AND module = $2 AND object_id = $3 AND mode = $4",
                message.guild.id,
                "chatfilter",
                message.channel.id,
                "channel",
            )
            if not res1:
                res2 = await self.bot.db.fetchrow(
                    "SELECT * FROM whitelist WHERE guild_id = $1 AND module = $2 AND object_id = $3 AND mode = $4",
                    message.guild.id,
                    "chatfilter",
                    message.author.id,
                    "user",
                )
                if not res2:
                    for result in check:
                        if result["word"] in await decrypt_message(message.content):
                            return await message.delete()

    @commands.Cog.listener("on_message_edit")
    async def invite_edit(self, before, after: discord.Message):
        if after.content == before.content:
            return
        message = after
        if not message.guild:
            return
        if isinstance(message.author, discord.User):
            return
        if message.author.bot:
            return
        if await Perms.has_perms(await self.bot.get_context(message), "manage_guild"):
            return
        invites = ["discord.gg/", ".gg/", "discord.com/invite/"]
        if any(invite in message.content for invite in invites):
            check = await self.bot.db.fetchrow(
                "SELECT * FROM antiinvite WHERE guild_id = $1", message.guild.id
            )
            if check is not None:
                res1 = await self.bot.db.fetchrow(
                    "SELECT * FROM whitelist WHERE guild_id = $1 AND module = $2 AND object_id = $3 AND mode = $4",
                    message.guild.id,
                    "antiinvite",
                    message.channel.id,
                    "channel",
                )
                if res1:
                    return
                res2 = await self.bot.db.fetchrow(
                    "SELECT * FROM whitelist WHERE guild_id = $1 AND module = $2 AND object_id = $3 AND mode = $4",
                    message.guild.id,
                    "antiinvite",
                    message.author.id,
                    "user",
                )
                if res2:
                    return
                if "discord.gg/" in message.content:
                    spl_word = "discord.gg/"
                elif ".gg/" in message.content:
                    spl_word = ".gg/"
                elif "discord.com/invite/" in message.content:
                    spl_word = "discord.com/invite/"

                linko = message.content.partition(spl_word)[2]
                link = linko.split()[0]
                data = await self.bot.session.json(DISCORD_API_LINK + link)
                try:
                    if int(data["guild"]["id"]) == message.guild.id:
                        return
                    await message.delete()
                    await message.author.timeout(
                        discord.utils.utcnow() + datetime.timedelta(minutes=1),
                        reason="AutoMod: Sending invites",
                    )
                    await message.channel.send(
                        embed=discord.Embed(
                            color=self.bot.color,
                            title="AutoMod",
                            description=f"{self.bot.warning} {message.author.mention}: You have been muted for **1 minute** for sending discord invites in this channel",
                        )
                    )
                except KeyError:
                    pass

    @commands.Cog.listener("on_message")
    async def invite_send(self, message: discord.Message):
        if not message.guild:
            return
        if isinstance(message.author, discord.User):
            return
        if message.author.bot:
            return
        if await Perms.has_perms(await self.bot.get_context(message), "manage_guild"):
            return
        invites = ["discord.gg/", ".gg/", "discord.com/invite/"]
        if any(invite in message.content for invite in invites):
            check = await self.bot.db.fetchrow(
                "SELECT * FROM antiinvite WHERE guild_id = $1", message.guild.id
            )
            if check is not None:
                res1 = await self.bot.db.fetchrow(
                    "SELECT * FROM whitelist WHERE guild_id = $1 AND module = $2 AND object_id = $3 AND mode = $4",
                    message.guild.id,
                    "antiinvite",
                    message.channel.id,
                    "channel",
                )
                if res1:
                    return
                res2 = await self.bot.db.fetchrow(
                    "SELECT * FROM whitelist WHERE guild_id = $1 AND module = $2 AND object_id = $3 AND mode = $4",
                    message.guild.id,
                    "antiinvite",
                    message.author.id,
                    "user",
                )
                if res2:
                    return
                if "discord.gg/" in message.content:
                    spl_word = "discord.gg/"
                elif ".gg/" in message.content:
                    spl_word = ".gg/"
                elif "discord.com/invite/" in message.content:
                    spl_word = "discord.com/invite/"

                linko = message.content.partition(spl_word)[2]
                link = linko.split()[0]
                data = await self.bot.session.json(DISCORD_API_LINK + link)
                try:
                    if int(data["guild"]["id"]) == message.guild.id:
                        return
                    await message.delete()
                    await message.author.timeout(
                        discord.utils.utcnow() + datetime.timedelta(minutes=5),
                        reason="AudoMod: Sending invites",
                    )
                    await message.channel.send(
                        embed=discord.Embed(
                            color=self.bot.color,
                            title="AutoMod",
                            description=f"{self.bot.warning} {message.author.mention}: You have been muted for **5 minutes** for sending discord invites in this channel",
                        )
                    )
                except KeyError:
                    pass

    @commands.Cog.listener("on_message")
    async def imageonly(self, message: Message):
        if not message.guild:
            return
        if isinstance(message.author, User):
            return
        if message.author.guild_permissions.manage_guild:
            return
        if message.author.bot:
            return
        if message.attachments:
            return
        check = await self.bot.db.fetchrow(
            "SELECT * FROM mediaonly WHERE channel_id = $1", message.channel.id
        )
        if check:
            try:
                await message.delete()
            except:
                pass

    @commands.Cog.listener("on_message")
    async def sticky(self, message: discord.Message):
        if message.author.bot:
            return
        stickym = await self.bot.db.fetchval(
            "SELECT key FROM stickym WHERE channel_id = $1", message.channel.id
        )
        if not stickym:
            return

        async for message in message.channel.history(limit=3):
            if message.author.id == self.bot.user.id:
                await message.delete()

        return await message.channel.send(stickym)


async def setup(bot: commands.AutoShardedBot) -> None:
    await bot.add_cog(Messages(bot))
